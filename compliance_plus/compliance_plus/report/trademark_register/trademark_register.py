# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{
			"label": _("Trademark"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Trademark",
			"width": 120,
		},
		{"label": _("Mark"), "fieldname": "mark", "fieldtype": "Data", "width": 180},
		{"label": _("Classes"), "fieldname": "classes", "fieldtype": "Data", "width": 110},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 170},
		{
			"label": _("Application Number"),
			"fieldname": "application_number",
			"fieldtype": "Data",
			"width": 150,
		},
		{"label": _("Filing Date"), "fieldname": "filing_date", "fieldtype": "Date", "width": 100},
		{
			"label": _("Registration Number"),
			"fieldname": "registration_number",
			"fieldtype": "Data",
			"width": 150,
		},
		{"label": _("Valid Until"), "fieldname": "valid_until", "fieldtype": "Date", "width": 100},
		{"label": _("Next Date"), "fieldname": "next_date", "fieldtype": "Date", "width": 100},
		{
			"label": _("Applicant"),
			"fieldname": "applicant",
			"fieldtype": "Link",
			"options": "Company",
			"width": 160,
		},
		{"label": _("Agent"), "fieldname": "agent", "fieldtype": "Link", "options": "Supplier", "width": 150},
	]


def get_data(filters: frappe._dict):
	conditions = {field: filters[field] for field in ("applicant", "status", "brand") if filters.get(field)}
	fields = [column["fieldname"] for column in get_columns() if column["fieldname"] != "classes"]
	rows = frappe.get_list("Trademark", filters=conditions, fields=fields, order_by="filing_date desc")
	classes: dict[str, list[str]] = {}
	if rows:
		for row in frappe.get_all(
			"Trademark Class",
			filters={"parenttype": "Trademark", "parent": ("in", [row.name for row in rows])},
			fields=["parent", "class_number"],
			order_by="class_number asc",
		):
			classes.setdefault(row.parent, []).append(str(row.class_number))
	for row in rows:
		row.classes = ", ".join(classes.get(row.name, []))
	return rows
