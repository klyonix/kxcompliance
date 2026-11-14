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

from kxcompliance.install import CLIENT_ROLE, ROLES
from kxcompliance.kx_compliance.register import is_approver

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
	people = []
	for user in users:
		role = next(role for role in order if role in roles[user.name])
		people.append(
			{
				"user": user.name,
				"full_name": user.full_name or user.name,
				"role": ROLE_LABELS[role],
				"enabled": bool(user.enabled),
				"last_login": str(user.last_login) if user.last_login else None,
				"is_me": user.name == frappe.session.user,
				# An administrator's access is managed in the Desk, not here.
				"locked": user.name in admins,
			}
		)
	return sorted(people, key=lambda person: (order.index(BY_LABEL[person["role"]]), person["full_name"]))


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
