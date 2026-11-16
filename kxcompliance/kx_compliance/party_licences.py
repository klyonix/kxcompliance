# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Check that a customer or supplier holds the licences a sale or purchase needs.

Hooked on validate and on_submit of the selling and buying documents in hooks.py. A rule that
blocks lets the document be saved as a draft, with a warning, and stops it being submitted until
a valid licence is recorded or a Compliance Manager allows that document once. It reads the
document and changes only the licence numbers field it is given for printing.
"""

import frappe
from frappe import _
from frappe.utils import add_days, formatdate, getdate, now_datetime, nowdate

from kxcompliance import scoped

# Document: (party type, checkbox on Licence Requirement, field naming the party, date field)
DOCUMENTS = {
	"Quotation": ("Customer", "check_quotation", "party_name", "transaction_date"),
	"Sales Order": ("Customer", "check_sales_order", "customer", "transaction_date"),
	"Delivery Note": ("Customer", "check_delivery_note", "customer", "posting_date"),
	"Sales Invoice": ("Customer", "check_sales_invoice", "customer", "posting_date"),
	"Purchase Order": ("Supplier", "check_purchase_order", "supplier", "transaction_date"),
	"Purchase Receipt": ("Supplier", "check_purchase_receipt", "supplier", "posting_date"),
	"Purchase Invoice": ("Supplier", "check_purchase_invoice", "supplier", "posting_date"),
}
GROUP_FIELDS = {"Customer": "customer_group", "Supplier": "supplier_group"}
SETTINGS = "KX Compliance Settings"
FIRM = "CA/CS Firm"
CHECK_FIELDS = tuple(check_field for _party_type, check_field, _field, _date in DOCUMENTS.values())
LICENCE_NUMBERS_FIELD = "customer_licence_numbers"


def checked_for_company(company: str | None) -> bool:
	"""Whether a company's sales and purchases are checked at all.

	On an organisation's site, always. On a CA/CS firm's site, only for the companies of a client
	the firm has switched the Licence Check on for (RK, 15 Nov 2026).
	"""
	if scoped.get_cached_value(SETTINGS, SETTINGS, "account_type") != FIRM:
		return True
	if not company:
		return False
	client = scoped.get_value("Company Compliance Profile", {"company": company}, "client")
	return bool(client and scoped.get_value("Compliance Client", client, "licence_check"))


def check_document(doc, method=None):
	party_type, check_field, party_field, date_field = DOCUMENTS[doc.doctype]
	if doc.doctype == "Quotation" and doc.get("quotation_to") != "Customer":
		return
	if not checked_for_company(doc.get("company")):
		return
	party = doc.get(party_field)
	if not party:
		return
	on = getdate(doc.get(date_field) or nowdate())

	if method == "validate" and doc.meta.has_field(LICENCE_NUMBERS_FIELD):
		doc.set(LICENCE_NUMBERS_FIELD, licence_numbers(party_type, party, on))

	failures = [
		(requirement, message)
		for requirement in applicable_requirements(doc, party_type, check_field, party)
		if (message := missing_licence(requirement, party_type, party, on))
	]
	if not failures:
		return
	if has_override(doc):
		if method == "on_submit":
			for requirement, message in failures:
				log_check(doc, party_type, party, requirement, "Overridden", message)
		return

	blocking = [(requirement, message) for requirement, message in failures if requirement.action == "Block"]
	if blocking and method == "validate":
		# A blocked document may still be saved as a draft; submitting it is what is blocked (RK,
		# 15 Nov 2026), so a manager can allow that draft once by its name.
		for requirement, message in blocking:
			log_draft_block(doc, party_type, party, requirement, message)
			frappe.msgprint(
				_(
					"{0} It can be saved as a draft, but not submitted until a valid licence is recorded or a Compliance Manager allows it once."
				).format(message),
				title=_("Licence Needed"),
				indicator="red",
			)
	elif blocking:
		messages = [message for _requirement, message in blocking]
		log_block_after_rollback(doc, party_type, party, blocking)
		frappe.throw("<br>".join(messages), title=_("Licence Needed"))

	for requirement, message in failures:
		if requirement.action == "Block":
			continue
		if method == "on_submit":
			log_check(doc, party_type, party, requirement, "Warned", message)
		else:
			frappe.msgprint(message, title=_("Licence Needed"), indicator="orange")


def applicable_requirements(doc, party_type: str, check_field: str, party: str) -> list:
	document_groups = {row.get("item_group") for row in doc.get("items", [])} - {None, ""}
	company = doc.get("company")
	return [
		requirement
		for requirement in requirements_for_party(party_type, party, check_field)
		if (not requirement.item_groups or set(requirement.item_groups) & document_groups)
		and (not requirement.companies or company in requirement.companies)
	]


def requirements_for_party(party_type: str, party: str, check_field: str | None = None) -> list:
	"""Active requirements that apply to this party, each with the item groups it is limited to."""
	filters = {"party_type": party_type, "is_active": 1}
	if check_field:
		filters[check_field] = 1
	requirements = scoped.get_all(
		"Licence Requirement",
		filters=filters,
		fields=["name", "item_type", "action", "grace_days", *CHECK_FIELDS],
		order_by="item_type asc",
	)
	if not requirements:
		return []
	names = [requirement.name for requirement in requirements]
	item_groups = rows_by_parent("Licence Requirement Item Group", names, "item_group")
	companies = rows_by_parent("Licence Requirement Company", names, "company")
	party_groups = rows_by_parent("Licence Requirement Party Group", names, "party_group")
	party_group = scoped.get_cached_value(party_type, party, GROUP_FIELDS[party_type])

	applicable = []
	for requirement in requirements:
		wanted_parties = party_groups.get(requirement.name)
		if wanted_parties and party_group not in wanted_parties:
			continue
		requirement.item_groups = sorted(item_groups.get(requirement.name, ()))
		requirement.companies = sorted(companies.get(requirement.name, ()))
		applicable.append(requirement)
	return applicable


def rows_by_parent(doctype: str, parents: list[str], fieldname: str) -> dict[str, set[str]]:
	result: dict[str, set[str]] = {}
	for row in scoped.get_all(doctype, filters={"parent": ("in", parents)}, fields=["parent", fieldname]):
		result.setdefault(row.parent, set()).add(row.get(fieldname))
	return result


def party_licence_items(party_type: str, party: str, item_type: str | None = None) -> list:
	"""The party's licences that are not cancelled, latest expiry first."""
	filters = {"holder_type": party_type, "holder": party, "is_cancelled": 0}
	if item_type:
		filters["item_type"] = item_type
	return scoped.get_all(
		"Compliance Item",
		filters=filters,
		fields=["name", "item_type", "reference_number", "status", "valid_from", "valid_until"],
		order_by="valid_until desc",
	)


def is_valid_on(licence, on, grace_days: int = 0) -> bool:
	return (not licence.valid_from or getdate(licence.valid_from) <= on) and (
		not licence.valid_until or getdate(add_days(licence.valid_until, grace_days)) >= on
	)


def valid_licences(party_type: str, party: str, on, item_type: str | None = None, grace_days: int = 0):
	return [
		licence
		for licence in party_licence_items(party_type, party, item_type)
		if is_valid_on(licence, on, grace_days)
	]


def licence_gap(requirement, licences: list, party_type: str, party: str, on) -> dict | None:
	"""Why the party's licences do not meet a requirement on a date, or None when they do.

	`licences` are the party's licences, latest expiry first, as party_licence_items gives them.
	"""
	of_type = [licence for licence in licences if licence.item_type == requirement.item_type]
	if any(is_valid_on(licence, on, requirement.grace_days or 0) for licence in of_type):
		return None
	latest = next((licence for licence in of_type if licence.valid_until), None)
	if latest:
		return {
			"result": "expired",
			"licence": latest.name,
			"message": _("{0} {1}'s {2} ({3}) expired on {4}.").format(
				_(party_type), party, requirement.item_type, latest.name, formatdate(latest.valid_until)
			),
		}
	return {
		"result": "missing",
		"licence": None,
		"message": _("{0} {1} has no {2} on record.").format(_(party_type), party, requirement.item_type),
	}


def missing_licence(requirement, party_type: str, party: str, on) -> str | None:
	licences = party_licence_items(party_type, party, requirement.item_type)
	gap = licence_gap(requirement, licences, party_type, party, on)
	return gap["message"] if gap else None


def licence_numbers(party_type: str, party: str, on) -> str:
	lines = []
	for licence in valid_licences(party_type, party, on):
		if not licence.reference_number:
			continue
		until = (
			" " + _("(valid until {0})").format(formatdate(licence.valid_until))
			if licence.valid_until
			else ""
		)
		lines.append(f"{licence.item_type}: {licence.reference_number}{until}")
	return "\n".join(lines)


def has_override(doc) -> bool:
	return not doc.is_new() and bool(
		scoped.exists("Licence Override", {"override_key": override_key(doc.doctype, doc.name)})
	)


def override_key(doctype: str, name: str) -> str:
	return f"{doctype}|{name}"


def log_check(doc, party_type: str, party: str, requirement, result: str, message: str):
	write_log_entry(
		{
			"result": result,
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"party_type": party_type,
			"party": party,
			"licence_requirement": requirement.name,
			"item_type": requirement.item_type,
			"checked_by": frappe.session.user,
			"message": message,
		}
	)


def write_log_entry(entry: dict):
	log = frappe.get_doc({"doctype": "Licence Check Log", "checked_on": now_datetime(), **entry})
	# An audit log must be kept even if the document it names is later deleted or renamed.
	log.flags.ignore_links = True
	log.insert(ignore_permissions=True)


def log_draft_block(doc, party_type: str, party: str, requirement, message: str):
	"""A draft saved without the licence, logged once per rule so the Blocks list shows it by name."""
	if not doc.name:
		return
	already = scoped.exists(
		"Licence Check Log",
		{
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"licence_requirement": requirement.name,
			"result": "Blocked",
		},
	)
	if not already:
		log_check(doc, party_type, party, requirement, "Blocked", message)


def log_block_after_rollback(doc, party_type: str, party: str, blocking: list):
	"""A block rolls the request back, so its log is queued to be written afterwards."""
	entries = [
		{
			"result": "Blocked",
			"reference_doctype": doc.doctype,
			"reference_name": None if doc.is_new() else doc.name,
			"party_type": party_type,
			"party": party,
			"licence_requirement": requirement.name,
			"item_type": requirement.item_type,
			"checked_by": frappe.session.user,
			"message": message,
		}
		for requirement, message in blocking
	]
	frappe.db.after_rollback.add(
		lambda: frappe.enqueue("kxcompliance.kx_compliance.party_licences.write_block_logs", entries=entries)
	)


def write_block_logs(entries: list[dict]):
	for entry in entries:
		write_log_entry(entry)
