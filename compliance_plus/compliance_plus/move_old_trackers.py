# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Move Compliance, Licence, Insurance and Subscription Tracker rows into Compliance Item.

The old rows are left in place, read-only, to check against. Each new item records the
row it came from under a unique key, so running this again moves only what is left.
A row that cannot be moved is logged and skipped, and the summary says so.

    bench --site SITE execute compliance_plus.compliance_plus.move_old_trackers.move_all
"""

import frappe
from frappe import _
from frappe.utils import cint, escape_html

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
	rows = frappe.get_all(doctype, fields=["*"], order_by="creation asc")
	moved_keys = set(
		frappe.get_all("Compliance Item", filters={"source_doctype": doctype}, pluck="source_key")
	)
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
			move_row(doctype, row, company)
			counts["moved"] += 1
		except Exception:
			frappe.db.rollback(save_point=SAVEPOINT)
			frappe.log_error(title=f"Could not move {doctype} {row.name} to Compliance Item")
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


def copy_attachments(doctype: str, source: str, item: str):
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
				"attached_to_doctype": "Compliance Item",
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
