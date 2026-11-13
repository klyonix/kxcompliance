# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Move the old trackers' rows into the records that replace them.

Compliance, Licence, Insurance and Subscription Tracker rows become Compliance Items;
Hearing Tracker rows become Legal Cases; Trademark Tracker rows become Trademarks;
Drug License and FSSAI rows on Customer become Compliance Items held by the customer.

The old rows are left in place, read-only, to check against. Each new item records the
row it came from under a unique key, so running this again moves only what is left.
A row that cannot be moved is logged and skipped, and the summary says so.

    bench --site SITE execute compliance_plus.compliance_plus.move_old_trackers.move_all
    bench --site SITE execute compliance_plus.compliance_plus.move_old_trackers.move_hearings
    bench --site SITE execute compliance_plus.compliance_plus.move_old_trackers.move_trademarks
    bench --site SITE execute compliance_plus.compliance_plus.move_old_trackers.move_customer_licences
"""

import re

import frappe
from frappe import _
from frappe.utils import cint, escape_html, getdate, nowdate

GENERIC_TYPES = {
	"Licence Tracker": ("Licence", "Licence"),
	"Insurance Tracker": ("Insurance", "Insurance"),
	"Subscription Tracker": ("Subscription", "Subscription"),
}
BILLING_CYCLES = {"Monthly": "Monthly", "Yearly": "Yearly"}
SAVEPOINT = "move_old_tracker_row"


def move_all() -> dict[str, dict[str, int]]:
	summary = {}
	for doctype in ("Compliance Tracker", "Licence Tracker", "Insurance Tracker", "Subscription Tracker"):
		if frappe.db.exists("DocType", doctype):
			summary[doctype] = move_doctype(doctype)
	return summary


def move_doctype(doctype: str) -> dict[str, int]:
	return move_rows(doctype, "Compliance Item", move_row)


def move_hearings() -> dict[str, int]:
	"""Hearing Tracker rows become Legal Cases, each with its hearing as a Legal Date."""
	if not frappe.db.exists("DocType", "Hearing Tracker"):
		return {"total": 0, "moved": 0, "already_moved": 0, "failed": 0}
	return move_rows("Hearing Tracker", "Legal Case", move_hearing_row)


def move_trademarks() -> dict[str, int]:
	"""Trademark Tracker rows become Trademarks, their activity and deadline a Legal Date."""
	if not frappe.db.exists("DocType", "Trademark Tracker"):
		return {"total": 0, "moved": 0, "already_moved": 0, "failed": 0}
	return move_rows("Trademark Tracker", "Trademark", move_trademark_row)


# The old customer licence tables another app adds to Customer, and the type each becomes.
CUSTOMER_LICENCE_TABLES = {"Drug License Details": "Drug Licence", "FSSAI Details": "FSSAI Licence"}


def move_customer_licences() -> dict[str, dict[str, int]]:
	"""Drug License and FSSAI rows on Customer become Compliance Items held by that customer."""
	return {
		doctype: move_rows(doctype, "Compliance Item", move_customer_licence_row)
		for doctype in CUSTOMER_LICENCE_TABLES
		if frappe.db.exists("DocType", doctype)
	}


def move_customer_licence_row(doctype: str, row, company: str) -> str:
	item_type = CUSTOMER_LICENCE_TABLES[doctype]
	customer_name = frappe.db.get_value("Customer", row.parent, "customer_name") or row.parent
	notes = ""
	if row.get("component"):
		notes = f"<p><strong>{_('Component')}:</strong> {escape_html(str(row.component))}</p>"
	item = frappe.get_doc(
		{
			"doctype": "Compliance Item",
			"title": f"{item_type} - {customer_name}",
			"item_type": item_type,
			"company": company,
			"holder_type": "Customer",
			"holder": row.parent,
			"reference_number": row.license_number,
			"valid_until": row.expiry_date,
			"responsible": responsible_for(row),
			"notes": notes,
			"source_doctype": doctype,
			"source_name": row.name,
			"source_key": source_key(doctype, row.name),
		}
	)
	item.flags.ignore_permissions = True  # a data move run by migrate, not by a person
	item.insert()
	return item.name


def move_rows(doctype: str, target: str, mover) -> dict[str, int]:
	rows = frappe.get_all(doctype, fields=["*"], order_by="creation asc")
	moved_keys = set(frappe.get_all(target, filters={"source_doctype": doctype}, pluck="source_key"))
	counts = {"total": len(rows), "moved": 0, "already_moved": 0, "failed": 0}
	if not rows:
		return counts

	company = default_company()
	for row in rows:
		if source_key(doctype, row.name) in moved_keys:
			counts["already_moved"] += 1
			continue
		frappe.db.savepoint(SAVEPOINT)
		try:
			mover(doctype, row, company)
			counts["moved"] += 1
		except Exception:
			frappe.db.rollback(save_point=SAVEPOINT)
			frappe.log_error(title=f"Could not move {doctype} {row.name} to {target}")
			counts["failed"] += 1

	assert counts["moved"] + counts["already_moved"] + counts["failed"] == counts["total"]
	return counts


def move_row(doctype: str, row, company: str) -> str:
	item = frappe.get_doc(
		{
			"doctype": "Compliance Item",
			"title": row.document_name,
			"item_type": item_type_for(doctype, row),
			"company": company,
			"issuing_authority": row.issuer_supplier,
			"issue_date": row.get("issue_date") or row.get("start_date"),
			"valid_from": row.get("issue_date") or row.get("start_date"),
			"valid_until": row.get("expiry_date") or row.get("end_date"),
			"billing_cycle": BILLING_CYCLES.get(row.get("subscription_type")),
			"responsible": responsible_for(row),
			"notes": notes_for(row),
			"source_doctype": doctype,
			"source_name": row.name,
			"source_key": source_key(doctype, row.name),
		}
	)
	if cint(row.enable_reminder) and cint(row.remind_before_days) > 0:
		item.append("reminders", {"days_before": cint(row.remind_before_days)})
	item.flags.ignore_permissions = True  # a data move run by migrate, not by a person
	item.insert()
	copy_attachments(doctype, row.name, item.name)
	return item.name


def move_hearing_row(doctype: str, row, company: str) -> str:
	case = frappe.get_doc(
		{
			"doctype": "Legal Case",
			"title": row.document_name,
			"case_type": "Litigation",
			"forum": "Other",
			"forum_name": row.issuer_supplier,
			"filing_date": row.issue_date,
			"company": company,
			"our_role": "Respondent",
			"responsible": responsible_for(row),
			"summary": notes_for(row)
			+ "<p>{}</p>".format(_("Our role was not recorded in the Hearing Tracker; check it.")),
			"source_doctype": doctype,
			"source_name": row.name,
			"source_key": source_key(doctype, row.name),
		}
	)
	case.flags.ignore_permissions = True  # a data move run by migrate, not by a person
	case.insert()
	if row.expiry_date:
		past = getdate(row.expiry_date) < getdate(nowdate())
		hearing = frappe.get_doc(
			{
				"doctype": "Legal Date",
				"reference_doctype": "Legal Case",
				"reference_name": case.name,
				"kind": "Hearing",
				"date": row.expiry_date,
				"status": "Done" if past else "Scheduled",
				"proceedings": _("Moved from the Hearing Tracker; the outcome was not recorded there.")
				if past
				else None,
			}
		)
		hearing.flags.ignore_permissions = True
		hearing.insert()
	copy_attachments(doctype, row.name, case.name, target="Legal Case")
	return case.name


TRADEMARK_STATUSES = {
	"Applied": "New Application",
	"Formality Check Pass": "Formalities Check Pass",
	"Marked For Exam": "Marked for Exam",
	"Objected": "Objected",
	"Advertised": "Accepted and Advertised",
	"Opposed": "Opposed",
	"Abandoned": "Abandoned",
	"Registered": "Registered",
}


def move_trademark_row(doctype: str, row, company: str) -> str:
	classes = sorted(
		{int(number) for number in re.findall(r"\d+", row.get("class") or "") if 1 <= int(number) <= 45}
	)
	notes = notes_for(row)
	for label, fieldname in (
		("Agent", "vendor"),
		("Agent contact", "vendor_point_of_contact"),
		("Agent phone", "vendor_contact_number"),
		("Follow-up", "follow_up_status"),
		("Class as recorded", "class"),
	):
		if row.get(fieldname):
			notes += f"<p><strong>{_(label)}:</strong> {escape_html(str(row.get(fieldname)))}</p>"
	trademark = frappe.get_doc(
		{
			"doctype": "Trademark",
			"mark": row.document_name,
			"brand": row.brand,
			"status": TRADEMARK_STATUSES.get(row.status, "New Application"),
			"classes": [{"class_number": number} for number in classes],
			"application_number": row.application_number,
			"filing_date": row.issue_date,
			"applicant": company,
			"responsible": responsible_for(row),
			"notes": notes,
			"source_doctype": doctype,
			"source_name": row.name,
			"source_key": source_key(doctype, row.name),
		}
	)
	trademark.flags.ignore_permissions = True  # a data move run by migrate, not by a person
	trademark.flags.moving = True  # old rows have no registration number to check
	trademark.insert()
	if row.expiry_date and trademark.renewal_item:
		item = frappe.get_doc("Compliance Item", trademark.renewal_item)
		item.valid_until = row.expiry_date
		item.flags.ignore_permissions = True
		item.save()
	if row.activity_deadline:
		past = getdate(row.activity_deadline) < getdate(nowdate())
		deadline = frappe.get_doc(
			{
				"doctype": "Legal Date",
				"reference_doctype": "Trademark",
				"reference_name": trademark.name,
				"kind": "Other",
				"date": row.activity_deadline,
				"purpose": row.activity,
				"status": "Done" if past else "Scheduled",
			}
		)
		deadline.flags.ignore_permissions = True
		deadline.insert()
	copy_attachments(doctype, row.name, trademark.name, target="Trademark")
	return trademark.name


def item_type_for(doctype: str, row) -> str:
	if doctype == "Compliance Tracker":
		name, category = row.compliance_category, "Other"
	else:
		name, category = GENERIC_TYPES[doctype]
	ensure_item_type(name, category)
	return name


def ensure_item_type(name: str, category: str):
	if frappe.db.exists("Compliance Item Type", name):
		return
	frappe.get_doc(
		{
			"doctype": "Compliance Item Type",
			"type_name": name,
			"category": category,
			"reminders": [{"days_before": 30}, {"days_before": 7}],
		}
	).insert(ignore_permissions=True)  # created by the data move


def responsible_for(row) -> str:
	for user in (row.in_charge, row.owner):
		if user and frappe.db.get_value("User", user, "enabled"):
			return user
	return "Administrator"


def notes_for(row) -> str:
	lines = []
	for label, fieldname in (
		("Type", "type"),
		("Agent", "agent_name"),
		("Contact Number", "contact_number"),
		("Status before the move", "status"),
	):
		value = row.get(fieldname)
		if value:
			lines.append(f"<p><strong>{_(label)}:</strong> {escape_html(str(value))}</p>")
	if row.description:
		lines.append(row.description)
	return "".join(lines)


def copy_attachments(doctype: str, source: str, item: str, target: str = "Compliance Item"):
	files = frappe.get_all(
		"File",
		filters={"attached_to_doctype": doctype, "attached_to_name": source, "is_folder": 0},
		fields=["file_name", "file_url", "is_private"],
	)
	for file in files:
		frappe.get_doc(
			{
				"doctype": "File",
				"file_name": file.file_name,
				"file_url": file.file_url,
				"is_private": file.is_private,
				"attached_to_doctype": target,
				"attached_to_name": item,
			}
		).insert(ignore_permissions=True)  # links the same stored file; nothing is copied


def default_company() -> str:
	"""The old trackers had no company, so their rows go to the site's default company."""
	company = frappe.defaults.get_global_default("company")
	if company:
		return company
	companies = frappe.get_all("Company", pluck="name", limit=2)
	if len(companies) == 1:
		return companies[0]
	frappe.throw(
		_(
			"Old tracker records need one Company to move into Compliance Item. "
			"Set a default company in Global Defaults, then run migrate again."
		)
	)


def source_key(doctype: str, name: str) -> str:
	return f"{doctype}|{name}"
