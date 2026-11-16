# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Move the Drug License and FSSAI rows another app adds to Customer into Compliance Items.

Each new item records the row it came from under a unique key, so running this again moves only
what is left. A row that cannot be moved is logged and skipped, and the summary says so.

    bench --site SITE execute kxcompliance.kx_compliance.move_customer_licences.move_customer_licences
"""

import frappe
from frappe import _
from frappe.utils import escape_html

from kxcompliance import scoped

SAVEPOINT = "move_customer_licence_row"

# The old customer licence tables another app adds to Customer, and the type each becomes.
CUSTOMER_LICENCE_TABLES = {"Drug License Details": "Drug Licence", "FSSAI Details": "FSSAI Licence"}


def move_customer_licences() -> dict[str, dict[str, int]]:
	"""Drug License and FSSAI rows on Customer become Compliance Items held by that customer."""
	return {
		doctype: move_rows(doctype, "Compliance Item", move_customer_licence_row)
		for doctype in CUSTOMER_LICENCE_TABLES
		if scoped.exists("DocType", doctype)
	}


def move_customer_licence_row(doctype: str, row, company: str) -> str:
	item_type = CUSTOMER_LICENCE_TABLES[doctype]
	customer_name = scoped.get_value("Customer", row.parent, "customer_name") or row.parent
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
	rows = scoped.get_all(doctype, fields=["*"], order_by="creation asc")
	moved_keys = set(scoped.get_all(target, filters={"source_doctype": doctype}, pluck="source_key"))
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


def responsible_for(row) -> str:
	for user in (row.in_charge, row.owner):
		if user and scoped.get_value("User", user, "enabled"):
			return user
	return "Administrator"


def default_company() -> str:
	"""The old licence rows had no company, so they go to the site's default company."""
	company = frappe.defaults.get_global_default("company")
	if company:
		return company
	companies = scoped.get_all("Company", pluck="name", limit=2)
	if len(companies) == 1:
		return companies[0]
	frappe.throw(
		_(
			"Old customer licence records need one Company to move into Compliance Item. "
			"Set a default company in Global Defaults, then run migrate again."
		)
	)


def source_key(doctype: str, name: str) -> str:
	return f"{doctype}|{name}"
