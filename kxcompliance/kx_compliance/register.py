# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Rules shared by the Compliance Item form and the daily job."""

import frappe
from frappe import _
from frappe.utils import date_diff, getdate

DEFAULT_DUE_SOON_DAYS = 30
DEFAULT_ESCALATE_AFTER_DAYS = 7

OPEN_RENEWAL_STATUSES = ("Planned", "Applied")
CLOSED_TASK_STATUSES = ("Filed", "Filed Late", "Not Applicable", "Cancelled")
APPROVER_ROLES = frozenset({"System Manager", "Compliance Manager"})


def get_settings():
	return frappe.get_cached_doc("KX Compliance Settings")


def due_soon_days() -> int:
	value = get_settings().due_soon_days
	return DEFAULT_DUE_SOON_DAYS if value is None else value


def escalate_after_days() -> int:
	value = get_settings().escalate_after_days
	return DEFAULT_ESCALATE_AFTER_DAYS if value is None else value


def compute_status(
	*,
	is_cancelled: bool,
	valid_until,
	renewal_status: str | None,
	grace_days: int,
	today,
	soon_days: int,
) -> str:
	"""An item's status by its dates and its open renewal (RK, 15 Nov 2026).

	A missing certificate is not a status: it hid the dates, and items marked so got no
	reminders. It is the separate `certificate_missing` flag. A planned renewal shows until the
	licence has run out, as Expired and Lapsed must stay visible.
	"""
	if is_cancelled:
		return "Cancelled"
	if renewal_status == "Applied":
		return "Renewal in Progress"
	if valid_until:
		valid_until = getdate(valid_until)
		today = getdate(today)
		if today > valid_until:
			return "Lapsed" if date_diff(today, valid_until) > grace_days else "Expired"
	if renewal_status == "Planned":
		return "Renewal Planned"
	if valid_until and date_diff(valid_until, today) <= soon_days:
		return "Due for Renewal"
	return "Active"


def is_certificate_missing(*, requires_document: bool, has_certificate: bool, is_cancelled: bool) -> bool:
	return bool(requires_document and not has_certificate and not is_cancelled)


def get_type_rules(item_types: list[str]) -> dict[str, frappe._dict]:
	if not item_types:
		return {}
	rows = frappe.get_all(
		"Compliance Item Type",
		filters={"name": ("in", list(set(item_types)))},
		fields=["name", "requires_document", "grace_days", "renewal_cycle_months"],
	)
	return {row.name: row for row in rows}


def open_renewal_statuses(items: list[str]) -> dict[str, str]:
	"""Each item's open renewal, Planned or Applied; an item has one at most."""
	if not items:
		return {}
	rows = frappe.get_all(
		"Compliance Renewal",
		filters={"compliance_item": ("in", items), "status": ("in", OPEN_RENEWAL_STATUSES)},
		fields=["compliance_item", "status"],
	)
	return {row.compliance_item: row.status for row in rows}


def is_approver(user: str | None = None) -> bool:
	return bool(APPROVER_ROLES & set(frappe.get_roles(user)))


PEOPLE_FIELDS = ("responsible", "reviewer")


def check_reassignment(doc):
	"""Once a record exists, only a Compliance Manager changes who is responsible for or reviews
	it; whoever creates one names them. Held here so every way of saving keeps the rule."""
	if doc.is_new() or is_approver():
		return
	for field in PEOPLE_FIELDS:
		if doc.has_value_changed(field):
			before = (doc.get_doc_before_save() or {}).get(field) or _("nobody")
			frappe.throw(
				_("Only a Compliance Manager can change {0} of {1} from {2} to {3}.").format(
					_(doc.meta.get_label(field)), doc.name, before, doc.get(field) or _("nobody")
				),
				frappe.PermissionError,
			)
