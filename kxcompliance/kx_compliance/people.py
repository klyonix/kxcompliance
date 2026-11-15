# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""The team, as the app's People screen shows it: who works in the app and in which role, inviting
someone new, changing a role and taking someone off the team. Compliance Managers only.

Only the app's own three roles are given or taken here. Someone with System Manager is left to
the Desk, so a manager can neither make an administrator nor lock one out.
"""

import frappe
from frappe import _
from frappe.utils import validate_email_address
from frappe.utils.password import update_password
from frappe.utils.password_strength import test_password_strength

from kxcompliance.install import CLIENT_ROLE, ROLES
from kxcompliance.kx_compliance.legal import CLOSED_CASE_STATUSES
from kxcompliance.kx_compliance.overview import PENDING_MARK_STATUSES
from kxcompliance.kx_compliance.register import CLOSED_TASK_STATUSES, is_approver

# The words the app uses for each role.
ROLE_LABELS = {
	"Compliance Manager": "Manager",
	"Compliance User": "Staff",
	"Compliance Auditor": "Auditor",
}
BY_LABEL = {label: role for role, label in ROLE_LABELS.items()}
PROTECTED = ("Administrator", "Guest")


def check_manager():
	if not is_approver():
		frappe.throw(_("Only a Compliance Manager can change who is on the team."), frappe.PermissionError)


def role_of(label: str) -> str:
	role = BY_LABEL.get(label)
	if not role:
		frappe.throw(_("Choose Manager, Staff or Auditor, not {0}.").format(label))
	return role


def team() -> list[dict]:
	"""Everyone with one of the app's roles, managers first."""
	check_manager()
	rows = frappe.get_all(
		"Has Role", filters={"role": ("in", ROLES), "parenttype": "User"}, fields=["parent", "role"]
	)
	roles: dict[str, set[str]] = {}
	for row in rows:
		roles.setdefault(row.parent, set()).add(row.role)
	names = [name for name in roles if name not in PROTECTED]
	if not names:
		return []
	admins = set(
		frappe.get_all(
			"Has Role",
			filters={"role": "System Manager", "parenttype": "User", "parent": ("in", names)},
			pluck="parent",
		)
	)
	users = frappe.get_all(
		"User",
		filters={"name": ("in", names)},
		fields=["name", "full_name", "enabled", "last_login"],
	)
	order = list(ROLE_LABELS)
	people = [person_row(user, roles[user.name], user.name in admins) for user in users]
	return sorted(people, key=lambda person: (order.index(BY_LABEL[person["role"]]), person["full_name"]))


def person_row(user, roles: set[str], admin: bool) -> dict:
	"""One person as the People screen shows them; `user` has name, full_name, enabled, last_login."""
	role = next(role for role in ROLE_LABELS if role in roles)
	return {
		"user": user.name,
		"full_name": user.full_name or user.name,
		"role": ROLE_LABELS[role],
		"enabled": bool(user.enabled),
		"last_login": str(user.last_login) if user.last_login else None,
		"is_me": user.name == frappe.session.user,
		# An administrator's access is managed in the Desk, not here.
		"locked": admin,
	}


def person(user: str) -> dict:
	"""One person on the team, for their page: their role, sign-in, and the open work they hold."""
	check_manager()
	roles = set(frappe.get_roles(user))
	if user in PROTECTED or not roles & set(ROLES):
		frappe.throw(_("{0} is not on the team.").format(user), frappe.DoesNotExistError)
	row = frappe.db.get_value("User", user, ["name", "full_name", "enabled", "last_login"], as_dict=True)
	return {
		**person_row(row, roles, "System Manager" in roles),
		"work": open_work(user),
		"can_email": outgoing_email(),
	}


def open_work(user: str) -> list[dict]:
	"""The open filings, register items, cases and trademarks someone is responsible for: each
	count with the filters it counted, so the app opens the list of exactly those."""
	kinds = (
		("Filings", "Compliance Task", [["status", "not in", list(CLOSED_TASK_STATUSES)]]),
		("Register items", "Compliance Item", [["is_cancelled", "=", 0]]),
		("Legal cases", "Legal Case", [["status", "not in", list(CLOSED_CASE_STATUSES)]]),
		("Trademarks", "Trademark", [["status", "in", list(PENDING_MARK_STATUSES)]]),
	)
	work = []
	for label, doctype, open_filters in kinds:
		filters = [["responsible", "=", user], *open_filters]
		work.append(
			{
				"label": label,
				"doctype": doctype,
				"filters": filters,
				"value": frappe.db.count(doctype, filters),
			}
		)
	return work


def outgoing_email() -> bool:
	return bool(frappe.db.exists("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}))


def invite(full_name: str, email: str, role: str) -> dict:
	"""Add someone to the team. A new person gets the welcome email to set a password; with no
	email account set up, the manager is given the link to pass on instead."""
	check_manager()
	role = role_of(role)
	email = (validate_email_address((email or "").strip(), throw=True) or "").lower()
	full_name = (full_name or "").strip()
	if not full_name:
		frappe.throw(_("Give the person's name."))
	existing = frappe.db.get_value("User", email, ["name", "user_type"], as_dict=True)
	if existing:
		return add_to_team(existing, role)
	first, _space, last = full_name.partition(" ")
	send = outgoing_email()
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first,
			"last_name": last,
			"user_type": "System User",
			"send_welcome_email": int(send),
			"roles": [{"role": role}],
		}
	)
	# A manager may add people to the team (checked above) without the right to edit every User;
	# only the app's own roles are given.
	user.insert(ignore_permissions=True)
	return {"user": user.name, "emailed": send, "link": None if send else sign_in_link(user)}


def add_to_team(existing, role: str) -> dict:
	roles = set(frappe.get_roles(existing.name))
	if CLIENT_ROLE in roles and not roles & set(ROLES):
		frappe.throw(
			_("{0} signs in as a client's login, so cannot also join the team.").format(existing.name)
		)
	if roles & set(ROLES):
		frappe.throw(_("{0} is already on the team; change their role in the list.").format(existing.name))
	user = frappe.get_doc("User", existing.name)
	user.flags.ignore_permissions = True  # the manager was checked; only an app role is added
	user.add_roles(role)
	return {"user": user.name, "emailed": False, "link": None}


def sign_in_link(user) -> str:
	"""A link to set a password, for a site that cannot send the welcome email yet."""
	return user._reset_password(send_email=False)


def check_changeable(user: str):
	if user in PROTECTED or user == frappe.session.user:
		frappe.throw(_("You cannot change your own role or remove yourself; ask another manager."))
	if "System Manager" in frappe.get_roles(user):
		frappe.throw(_("{0} is an administrator; their access is changed in the Desk.").format(user))
	if not set(frappe.get_roles(user)) & set(ROLES):
		frappe.throw(_("{0} is not on the team.").format(user))


def set_role(user: str, role: str) -> dict:
	check_manager()
	role = role_of(role)
	check_changeable(user)
	doc = frappe.get_doc("User", user)
	doc.flags.ignore_permissions = True  # the manager was checked; only the app's roles change
	doc.remove_roles(*[other for other in ROLES if other != role])
	doc.add_roles(role)
	return {"user": user, "role": ROLE_LABELS[role]}


def remove(user: str) -> dict:
	"""Take someone off the team: they lose the app's roles. Their work stays as it is."""
	check_manager()
	check_changeable(user)
	doc = frappe.get_doc("User", user)
	doc.flags.ignore_permissions = True  # the manager was checked; only the app's roles are taken
	doc.remove_roles(*ROLES)
	return {"user": user}


def new_sign_in_link(user: str) -> dict:
	"""A fresh link to set a password, for someone added who has never signed in.

	Only for them: a link for someone already using the app would let a manager sign in as that
	person, so they reset their own password instead.
	"""
	check_manager()
	check_changeable(user)
	if frappe.db.get_value("User", user, "last_login"):
		frappe.throw(_("{0} has signed in before; they can reset their own password.").format(user))
	return {"user": user, "link": sign_in_link(frappe.get_doc("User", user))}


def send_password_reset(user: str) -> dict:
	"""Email someone Frappe's link to set a new password themselves; the manager never sees it."""
	check_manager()
	check_changeable(user)
	if not outgoing_email():
		frappe.throw(
			_(
				"This site cannot send email yet, so the reset link cannot be sent. Set a temporary password instead."
			)
		)
	frappe.get_doc("User", user)._reset_password(send_email=True)
	return {"user": user, "emailed": True}


MIN_PASSWORD_LENGTH = 8


def set_temporary_password(user: str, password: str) -> dict:
	"""Give someone a password to pass on in person, for a site that cannot send email.

	It ends every session they have open, and the change is noted on their user record.
	"""
	check_manager()
	check_changeable(user)
	if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
		frappe.throw(_("A password needs at least {0} characters.").format(MIN_PASSWORD_LENGTH))
	weak = check_strength(user, password)
	if weak:
		frappe.throw(weak)
	update_password(user, password, logout_all_sessions=True)
	frappe.get_doc("User", user).add_comment(
		"Info", _("{0} set a temporary password from the People screen.").format(frappe.session.user)
	)
	return {"user": user}


def check_strength(user: str, password: str) -> str:
	"""Why the site's password policy refuses this password, or "" when it passes (or is off)."""
	if not frappe.get_system_settings("enable_password_policy"):
		return ""
	details = frappe.db.get_value(
		"User", user, ["first_name", "middle_name", "last_name", "email", "birth_date"]
	)
	result = test_password_strength(password, user_inputs=details)
	minimum = frappe.get_system_settings("minimum_password_score") or 0
	if (result.get("score") or 0) >= int(minimum) and result.get("score"):
		return ""
	feedback = result.get("feedback") or {}
	return " ".join(filter(None, [_("This password is too easy to guess."), feedback.get("warning")]))
