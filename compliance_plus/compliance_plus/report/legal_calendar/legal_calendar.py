# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
		{"label": _("Kind"), "fieldname": "kind", "fieldtype": "Data", "width": 160},
		{"label": _("For"), "fieldname": "reference_doctype", "fieldtype": "Data", "width": 110},
		{
			"label": _("Record"),
			"fieldname": "reference_name",
			"fieldtype": "Dynamic Link",
			"options": "reference_doctype",
			"width": 130,
		},
		{"label": _("Title"), "fieldname": "reference_title", "fieldtype": "Data", "width": 220},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Purpose"), "fieldname": "purpose", "fieldtype": "Data", "width": 200},
		{
			"label": _("Responsible"),
			"fieldname": "responsible",
			"fieldtype": "Link",
			"options": "User",
			"width": 160,
		},
		{
			"label": _("Legal Date"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Legal Date",
			"width": 120,
		},
	]


def get_data(filters: frappe._dict):
	start = getdate(filters.get("from_date") or nowdate())
	end = getdate(filters.get("to_date") or add_days(start, 30))
	conditions = {"date": ("between", [start, end])}
	for field in ("reference_doctype", "kind", "status", "responsible"):
		if filters.get(field):
			conditions[field] = filters[field]
	return frappe.get_list(
		"Legal Date",
		filters=conditions,
		fields=[column["fieldname"] for column in get_columns()],
		order_by="date asc",
	)
