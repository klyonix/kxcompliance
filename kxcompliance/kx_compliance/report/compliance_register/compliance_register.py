# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _

FILTER_FIELDS = ("company", "branch", "state", "item_type", "status", "responsible")


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{
			"label": _("Item"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Compliance Item",
			"width": 140,
		},
		{"label": _("Title"), "fieldname": "title", "fieldtype": "Data", "width": 220},
		{
			"label": _("Type"),
			"fieldname": "item_type",
			"fieldtype": "Link",
			"options": "Compliance Item Type",
			"width": 180,
		},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 140},
		{"label": _("Reference Number"), "fieldname": "reference_number", "fieldtype": "Data", "width": 150},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 160,
		},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120},
		{"label": _("State"), "fieldname": "state", "fieldtype": "Data", "width": 120},
		{"label": _("Valid Until"), "fieldname": "valid_until", "fieldtype": "Date", "width": 110},
		{
			"label": _("Responsible"),
			"fieldname": "responsible",
			"fieldtype": "Link",
			"options": "User",
			"width": 180,
		},
		{
			"label": _("Reviewer"),
			"fieldname": "reviewer",
			"fieldtype": "Link",
			"options": "User",
			"width": 180,
		},
	]


def get_data(filters: frappe._dict):
	conditions = {field: filters[field] for field in FILTER_FIELDS if filters.get(field)}
	return frappe.get_list(
		"Compliance Item",
		filters=conditions,
		fields=[column["fieldname"] for column in get_columns()],
		order_by="valid_until asc",
	)
