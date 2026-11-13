# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Check that a customer or supplier holds the licences a sale or purchase needs.

Hooked on validate of the selling and buying documents in hooks.py. It reads the
document and changes only the licence numbers field it is given for printing.
"""

import frappe
from frappe import _
from frappe.utils import add_days, formatdate, getdate, now_datetime, nowdate

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
LICENCE_NUMBERS_FIELD = "customer_licence_numbers"


def check_document(doc, method=None):
	party_type, check_field, party_field, date_field = DOCUMENTS[doc.doctype]
	if doc.doctype == "Quotation" and doc.get("quotation_to") != "Customer":
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
	if blocking:
		messages = [message for _requirement, message in blocking]
		log_block_after_rollback(doc, party_type, party, blocking)
		frappe.throw("<br>".join(messages), title=_("Licence Needed"))

	for requirement, message in failures:
		if method == "on_submit":
			log_check(doc, party_type, party, requirement, "Warned", message)
		else:
			frappe.msgprint(message, title=_("Licence Needed"), indicator="orange")


def applicable_requirements(doc, party_type: str, check_field: str, party: str) -> list:
	requirements = frappe.get_all(
		"Licence Requirement",
		filters={"party_type": party_type, "is_active": 1, check_field: 1},
		fields=["name", "item_type", "action", "grace_days"],
	)
	if not requirements:
		return []
	names = [requirement.name for requirement in requirements]
	item_groups = rows_by_parent("Licence Requirement Item Group", names, "item_group")
	party_groups = rows_by_parent("Licence Requirement Party Group", names, "party_group")
	party_group = frappe.get_cached_value(party_type, party, GROUP_FIELDS[party_type])
	document_groups = {row.get("item_group") for row in doc.get("items", [])} - {None, ""}

	applicable = []
	for requirement in requirements:
		wanted_items = item_groups.get(requirement.name)
		wanted_parties = party_groups.get(requirement.name)
		if wanted_items and not (wanted_items & document_groups):
			continue
		if wanted_parties and party_group not in wanted_parties:
			continue
		applicable.append(requirement)
	return applicable


def rows_by_parent(doctype: str, parents: list[str], fieldname: str) -> dict[str, set[str]]:
	result: dict[str, set[str]] = {}
	for row in frappe.get_all(doctype, filters={"parent": ("in", parents)}, fields=["parent", fieldname]):
		result.setdefault(row.parent, set()).add(row.get(fieldname))
	return result


def valid_licences(party_type: str, party: str, on, item_type: str | None = None, grace_days: int = 0):
	filters = {"holder_type": party_type, "holder": party, "is_cancelled": 0}
	if item_type:
		filters["item_type"] = item_type
	licences = frappe.get_all(
		"Compliance Item",
		filters=filters,
		fields=["name", "item_type", "reference_number", "valid_from", "valid_until"],
		order_by="valid_until desc",
	)
	return [
		licence
		for licence in licences
		if (not licence.valid_from or getdate(licence.valid_from) <= on)
		and (not licence.valid_until or getdate(add_days(licence.valid_until, grace_days)) >= on)
	]


def missing_licence(requirement, party_type: str, party: str, on) -> str | None:
	if valid_licences(party_type, party, on, requirement.item_type, requirement.grace_days or 0):
		return None
	latest = frappe.db.get_value(
		"Compliance Item",
		{"holder_type": party_type, "holder": party, "item_type": requirement.item_type, "is_cancelled": 0},
		["name", "valid_until"],
		as_dict=True,
		order_by="valid_until desc",
	)
	if latest and latest.valid_until:
		return _("{0} {1}'s {2} ({3}) expired on {4}.").format(
			_(party_type), party, requirement.item_type, latest.name, formatdate(latest.valid_until)
		)
	return _("{0} {1} has no {2} on record.").format(_(party_type), party, requirement.item_type)


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
		frappe.db.exists("Licence Override", {"override_key": override_key(doc.doctype, doc.name)})
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
		lambda: frappe.enqueue(
			"compliance_plus.compliance_plus.party_licences.write_block_logs", entries=entries
		)
	)


def write_block_logs(entries: list[dict]):
	for entry in entries:
		write_log_entry(entry)
