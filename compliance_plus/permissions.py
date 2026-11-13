# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Who sees which compliance records.

Compliance Managers, Auditors and System Managers see everything. Anyone else reaches
an item or a statutory task only as its Responsible person or its Reviewer, and a
renewal only through its item.
"""

import frappe

UNRESTRICTED_ROLES = frozenset(
	{"Administrator", "System Manager", "Compliance Manager", "Compliance Auditor"}
)


def is_restricted(user: str) -> bool:
	return not (UNRESTRICTED_ROLES & set(frappe.get_roles(user)))


def holder_conditions(doctype: str, user: str | None) -> str:
	user = user or frappe.session.user
	if not is_restricted(user):
		return ""
	# permission_query_conditions must return SQL; the user is quoted by frappe.db.escape.
	quoted = frappe.db.escape(user)
	return f"(`tab{doctype}`.`responsible` = {quoted} or `tab{doctype}`.`reviewer` = {quoted})"


def item_query_conditions(user: str | None = None) -> str:
	return holder_conditions("Compliance Item", user)


def task_query_conditions(user: str | None = None) -> str:
	return holder_conditions("Compliance Task", user)


def renewal_query_conditions(user: str | None = None) -> str:
	user = user or frappe.session.user
	if not is_restricted(user):
		return ""
	quoted = frappe.db.escape(user)
	return (
		"`tabCompliance Renewal`.`compliance_item` in (select `name` from `tabCompliance Item`"
		f" where `responsible` = {quoted} or `reviewer` = {quoted})"
	)


def has_item_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if not is_restricted(user):
		return True
	return user in (doc.responsible, doc.reviewer)


has_task_permission = has_item_permission


def has_renewal_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if not is_restricted(user):
		return True
	if not doc.compliance_item:
		return True
	holders = frappe.db.get_value(
		"Compliance Item", doc.compliance_item, ["responsible", "reviewer"], as_dict=True
	)
	return bool(holders) and user in (holders.responsible, holders.reviewer)
