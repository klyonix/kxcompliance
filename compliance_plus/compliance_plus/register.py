# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Rules shared by the Compliance Item form and the daily job."""

import frappe
from frappe.utils import date_diff, getdate

DEFAULT_DUE_SOON_DAYS = 30
DEFAULT_ESCALATE_AFTER_DAYS = 7

OPEN_RENEWAL_STATUSES = ("Planned", "Applied")
CLOSED_TASK_STATUSES = ("Filed", "Filed Late", "Not Applicable", "Cancelled")
APPROVER_ROLES = frozenset({"System Manager", "Compliance Manager"})


def get_settings():
	return frappe.get_cached_doc("Compliance Plus Settings")


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
	has_certificate: bool,
	requires_document: bool,
	renewal_applied: bool,
	grace_days: int,
	today,
	soon_days: int,
) -> str:
	if is_cancelled:
		return "Cancelled"
	if requires_document and not has_certificate:
		return "Draft"
	if renewal_applied:
		return "Renewal in Progress"
	if not valid_until:
		return "Active"

	valid_until = getdate(valid_until)
	today = getdate(today)
	if today > valid_until:
		return "Lapsed" if date_diff(today, valid_until) > grace_days else "Expired"
	if date_diff(valid_until, today) <= soon_days:
		return "Due for Renewal"
	return "Active"


def get_type_rules(item_types: list[str]) -> dict[str, frappe._dict]:
	if not item_types:
		return {}
	rows = frappe.get_all(
		"Compliance Item Type",
		filters={"name": ("in", list(set(item_types)))},
		fields=["name", "requires_document", "grace_days", "renewal_cycle_months"],
	)
	return {row.name: row for row in rows}


def items_with_applied_renewal(items: list[str]) -> set[str]:
	if not items:
		return set()
	return set(
		frappe.get_all(
			"Compliance Renewal",
			filters={"compliance_item": ("in", items), "status": "Applied"},
			pluck="compliance_item",
		)
	)


def is_approver(user: str | None = None) -> bool:
	return bool(APPROVER_ROLES & set(frappe.get_roles(user)))
