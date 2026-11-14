# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Who sees which compliance records.

Compliance Managers, Auditors and System Managers see everything. Anyone else reaches
an item, a statutory task or a legal case as its Responsible person or its Reviewer, and
a renewal or a Legal Date through the record it belongs to. In a CA/CS firm, someone on a
client's team also sees every record of that client's companies (clients.py gives them the
access, and a User Permission keeps them to those companies). A client's own login sees its
client's companies the same way, only reading (its role has no write permission) and without
the firm's remarks and notes, which are at permission level 1.
"""

import frappe
from frappe.utils.caching import request_cache

UNRESTRICTED_ROLES = frozenset(
	{"Administrator", "System Manager", "Compliance Manager", "Compliance Auditor"}
)


def is_restricted(user: str) -> bool:
	return not (UNRESTRICTED_ROLES & set(frappe.get_roles(user)))


@request_cache
def client_companies_of(user: str) -> tuple[str, ...]:
	"""The companies a person sees in full because they are on the client's team."""
	return tuple(
		sorted(set(frappe.get_all("Compliance Client Access", filters={"user": user}, pluck="company")))
	)


def company_condition(column: str, user: str) -> str:
	companies = client_companies_of(user)
	if not companies:
		return ""
	quoted = ", ".join(frappe.db.escape(company) for company in companies)
	return f" or {column} in ({quoted})"


def holder_conditions(doctype: str, user: str | None, company_field: str = "company") -> str:
	user = user or frappe.session.user
	if not is_restricted(user):
		return ""
	# permission_query_conditions must return SQL; the user is quoted by frappe.db.escape.
	quoted = frappe.db.escape(user)
	return (
		f"(`tab{doctype}`.`responsible` = {quoted} or `tab{doctype}`.`reviewer` = {quoted}"
		f"{company_condition(f'`tab{doctype}`.`{company_field}`', user)})"
	)


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
		f" where `responsible` = {quoted} or `reviewer` = {quoted}{company_condition('`company`', user)})"
	)


def holds_or_serves(doc, user: str, company: str | None) -> bool:
	return user in (doc.responsible, doc.reviewer) or (company or "") in client_companies_of(user)


def has_item_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if not is_restricted(user):
		return True
	return holds_or_serves(doc, user, doc.get("company"))


has_task_permission = has_item_permission
has_legal_case_permission = has_item_permission


def has_trademark_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if not is_restricted(user):
		return True
	return holds_or_serves(doc, user, doc.applicant)


def trademark_query_conditions(user: str | None = None) -> str:
	return holder_conditions("Trademark", user, company_field="applicant")


def legal_case_query_conditions(user: str | None = None) -> str:
	return holder_conditions("Legal Case", user)


def legal_date_query_conditions(user: str | None = None) -> str:
	user = user or frappe.session.user
	conditions = holder_conditions("Legal Date", user)
	companies = client_companies_of(user) if conditions else ()
	if not companies:
		return conditions
	# A date belongs to a case or trademark of a client's company.
	quoted = ", ".join(frappe.db.escape(company) for company in companies)
	return (
		f"({conditions} or `tabLegal Date`.`reference_name` in"
		f" (select `name` from `tabLegal Case` where `company` in ({quoted})"
		f" union select `name` from `tabTrademark` where `applicant` in ({quoted})))"
	)


def has_legal_date_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	"""A Legal Date is reached through the case or trademark it belongs to."""
	user = user or frappe.session.user
	if not is_restricted(user):
		return True
	if not (doc.reference_doctype and doc.reference_name):
		return True
	company_field = "applicant" if doc.reference_doctype == "Trademark" else "company"
	holders = frappe.db.get_value(
		doc.reference_doctype,
		doc.reference_name,
		["responsible", "reviewer", f"{company_field} as company"],
		as_dict=True,
	)
	return bool(holders) and holds_or_serves(holders, user, holders.company)


def has_renewal_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if not is_restricted(user):
		return True
	if not doc.compliance_item:
		return True
	holders = frappe.db.get_value(
		"Compliance Item", doc.compliance_item, ["responsible", "reviewer", "company"], as_dict=True
	)
	return bool(holders) and holds_or_serves(holders, user, holders.company)


def client_query_conditions(user: str | None = None) -> str:
	"""Firm staff see the clients they are on the team of, or manage the relationship of; a
	client's login sees its own client."""
	user = user or frappe.session.user
	if not is_restricted(user):
		return ""
	quoted = frappe.db.escape(user)
	return (
		f"(`tabCompliance Client`.`relationship_manager` = {quoted} or `tabCompliance Client`.`name` in"
		f" (select `parent` from `tabCompliance Client Member` where `user` = {quoted}"
		f" union select `parent` from `tabCompliance Client Login` where `user` = {quoted} and `enabled` = 1))"
	)


def has_client_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if not is_restricted(user):
		return True
	return (
		user == doc.relationship_manager
		or user in {row.user for row in doc.team}
		or user in {row.user for row in doc.logins if row.enabled}
	)
