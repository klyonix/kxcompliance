# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model import get_permitted_fields

FILTER_FIELDS = ("company", "case_type", "forum", "status", "risk", "responsible")


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	columns = permitted_columns()
	return columns, get_data(filters, columns)


def permitted_columns():
	# Amount and risk are for Compliance Managers and Auditors; others see the cases without them.
	readable = set(get_permitted_fields("Legal Case")) | {"name"}
	return [column for column in get_columns() if column["fieldname"] in readable]


def get_columns():
	return [
		{"label": _("Case"), "fieldname": "name", "fieldtype": "Link", "options": "Legal Case", "width": 130},
		{"label": _("Title"), "fieldname": "title", "fieldtype": "Data", "width": 220},
		{"label": _("Type"), "fieldname": "case_type", "fieldtype": "Data", "width": 150},
		{"label": _("Forum"), "fieldname": "forum", "fieldtype": "Data", "width": 140},
		{"label": _("Case Number"), "fieldname": "case_number", "fieldtype": "Data", "width": 140},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 140},
		{"label": _("Next Date"), "fieldname": "next_date", "fieldtype": "Date", "width": 100},
		{"label": _("Risk"), "fieldname": "risk", "fieldtype": "Data", "width": 90},
		{
			"label": _("Amount Involved"),
			"fieldname": "amount_involved",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 160,
		},
		{
			"label": _("Advocate"),
			"fieldname": "advocate",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 160,
		},
		{
			"label": _("Responsible"),
			"fieldname": "responsible",
			"fieldtype": "Link",
			"options": "User",
			"width": 160,
		},
	]


def get_data(filters: frappe._dict, columns: list[dict]):
	fields = [column["fieldname"] for column in columns]
	conditions = {field: filters[field] for field in FILTER_FIELDS if filters.get(field) and field in fields}
	return frappe.get_list(
		"Legal Case",
		filters=conditions,
		fields=fields,
		order_by="next_date asc",
	)
