# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Handing one person's open work to another, when they leave, go on leave or change clients
(RK, 15 Nov 2026): the open filings, register items, cases, trademarks, scheduled legal dates and
document requests they are responsible for, review or asked for, and their place as a company's
default person, an obligation's holder, a client's relationship manager and on a client's team.

A manager sees what would move, then starts it. It runs in the background, because a busy person
can hold hundreds of records and each is saved properly, so its history and rules apply; the
manager is told when it is done, with anything that could not move.
"""

import frappe
from frappe import _
from frappe.utils import escape_html

from kxcompliance.kx_compliance.document_requests import OPEN_STATUSES as OPEN_REQUEST_STATUSES
from kxcompliance.kx_compliance.legal import CLOSED_CASE_STATUSES, ENDED_MARK_STATUSES
from kxcompliance.kx_compliance.register import CLOSED_TASK_STATUSES

# The records that move: (what they are called, doctype, which are still open, the people fields).
RECORDS = (
	("Filings", "Compliance Task", {"status": ("not in", CLOSED_TASK_STATUSES)}, ("responsible", "reviewer")),
	("Register items", "Compliance Item", {"is_cancelled": 0}, ("responsible", "reviewer")),
	("Legal cases", "Legal Case", {"status": ("not in", CLOSED_CASE_STATUSES)}, ("responsible", "reviewer")),
	("Trademarks", "Trademark", {"status": ("not in", ENDED_MARK_STATUSES)}, ("responsible", "reviewer")),
	("Hearings and deadlines", "Legal Date", {"status": "Scheduled"}, ("responsible", "reviewer")),
	("Document requests", "Document Request", {"status": ("in", OPEN_REQUEST_STATUSES)}, ("requested_by",)),
)
# Save this many records, then commit, so locks stay short; a record that fails is undone alone.
BATCH = 50
SAVEPOINT = "handover"


def held_by(user: str, doctype: str, open_filters: dict, fields: tuple) -> list[str]:
	"""The open records of one kind where the person is in any of the people fields."""
	names: set[str] = set()
	for field in fields:
		names.update(frappe.get_all(doctype, filters={**open_filters, field: user}, pluck="name"))
	return sorted(names)


def companies_of(user: str) -> list[str]:
	"""The companies whose defaults or obligations name the person."""
	names = set(
		frappe.get_all(
			"Company Compliance Profile",
			or_filters={"default_responsible": user, "default_reviewer": user},
			pluck="name",
		)
	)
	names.update(
		frappe.get_all(
			"Company Obligation",
			or_filters={"responsible": user, "reviewer": user},
			filters={"parenttype": "Company Compliance Profile"},
			pluck="parent",
		)
	)
	return sorted(names)


def clients_of(user: str) -> list[str]:
	"""The clients the person manages or is on the team of."""
	names = set(frappe.get_all("Compliance Client", filters={"relationship_manager": user}, pluck="name"))
	names.update(
		frappe.get_all(
			"Compliance Client Member",
			filters={"user": user, "parenttype": "Compliance Client"},
			pluck="parent",
		)
	)
	return sorted(names)


def preview(user: str) -> list[dict]:
	"""What a hand-over of this person's work would move, kind by kind, with how many of each."""
	counts = [
		{"label": label, "count": len(held_by(user, doctype, filters, fields))}
		for label, doctype, filters, fields in RECORDS
	]
	obligations = frappe.get_all(
		"Company Obligation",
		or_filters={"responsible": user, "reviewer": user},
		filters={"parenttype": "Company Compliance Profile"},
		pluck="name",
	)
	counts += [
		{"label": "Companies (their defaults and obligations)", "count": len(companies_of(user))},
		{"label": "Obligations they handle", "count": len(obligations)},
		{"label": "Clients they look after", "count": len(clients_of(user))},
	]
	return counts


def run(from_user: str, to_user: str, by: str):
	"""Background job: move the work, then tell the manager who started it what moved."""
	frappe.set_user(by)
	moved, failed = 0, []
	for _label, doctype, filters, fields in RECORDS:
		for name in held_by(from_user, doctype, filters, fields):
			if move_record(doctype, name, fields, from_user, to_user):
				moved += 1
			else:
				failed.append(f"{_(doctype)} {name}")
			if (moved + len(failed)) % BATCH == 0:
				# A job may commit as it goes, so one failure later loses nothing done before it.
				frappe.db.commit()
	for name in companies_of(from_user):
		if not move_on_profile(name, from_user, to_user):
			failed.append(f"{_('Company')} {name}")
	for name in clients_of(from_user):
		if not move_on_client(name, from_user, to_user):
			failed.append(f"{_('Client')} {name}")
	# The work is done; the notice below goes out whatever happens to it.
	frappe.db.commit()
	tell_manager(by, from_user, to_user, moved, failed)


def move_record(doctype: str, name: str, fields: tuple, from_user: str, to_user: str) -> bool:
	frappe.db.savepoint(SAVEPOINT)
	try:
		doc = frappe.get_doc(doctype, name)
		for field in fields:
			if doc.get(field) == from_user:
				doc.set(field, to_user)
		# Someone cannot review their own work: if the new person was its reviewer, it has none now.
		if doc.meta.has_field("reviewer") and doc.get("reviewer") == doc.get("responsible"):
			doc.reviewer = None
		doc.save()
		return True
	except Exception:
		frappe.db.rollback(save_point=SAVEPOINT)
		frappe.log_error(title=f"Hand-over: {doctype} {name} could not move")
		return False


def move_on_profile(name: str, from_user: str, to_user: str) -> bool:
	doc = frappe.get_doc("Company Compliance Profile", name)
	changed = False
	for field in ("default_responsible", "default_reviewer"):
		if doc.get(field) == from_user:
			doc.set(field, to_user)
			changed = True
	if doc.default_reviewer and doc.default_reviewer == doc.default_responsible:
		doc.default_reviewer = None
	for row in doc.obligations:
		for field in ("responsible", "reviewer"):
			if row.get(field) == from_user:
				row.set(field, to_user)
				changed = True
		if row.reviewer and row.reviewer == row.responsible:
			row.reviewer = None
	if not changed:
		return True
	frappe.db.savepoint(SAVEPOINT)
	try:
		doc.save()
		return True
	except Exception:
		frappe.db.rollback(save_point=SAVEPOINT)
		frappe.log_error(title=f"Hand-over: company {name} could not move")
		return False


def move_on_client(name: str, from_user: str, to_user: str) -> bool:
	doc = frappe.get_doc("Compliance Client", name)
	changed = False
	if doc.relationship_manager == from_user:
		doc.relationship_manager = to_user
		changed = True
	members = [row.user for row in doc.team]
	if from_user in members:
		# The new person takes their place on the team, once.
		doc.team = [row for row in doc.team if row.user != from_user]
		if to_user not in members:
			doc.append("team", {"user": to_user})
		changed = True
	if not changed:
		return True
	frappe.db.savepoint(SAVEPOINT)
	try:
		doc.save()
		return True
	except Exception:
		frappe.db.rollback(save_point=SAVEPOINT)
		frappe.log_error(title=f"Hand-over: client {name} could not move")
		return False


def tell_manager(manager: str, from_user: str, to_user: str, moved: int, failed: list[str]):
	from kxcompliance.kx_compliance.reminders import notify

	names = dict(
		frappe.get_all(
			"User", filters={"name": ("in", [from_user, to_user])}, fields=["name", "full_name"], as_list=True
		)
	)
	subject = _("{0}'s work is now with {1}").format(
		names.get(from_user) or from_user, names.get(to_user) or to_user
	)
	lines = [_("{0} records moved, with their companies, obligations and clients.").format(moved)]
	if failed:
		lines.append(_("These could not move; open each to see why: {0}").format(", ".join(failed[:20])))
	body = "".join(f"<p>{escape_html(line)}</p>" for line in lines)
	notify([manager], subject, body, "User", from_user)
