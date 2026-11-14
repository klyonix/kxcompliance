# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Held By"), "fieldname": "holder_type", "fieldtype": "Data", "width": 100},
		{
			"label": _("Party"),
			"fieldname": "holder",
			"fieldtype": "Dynamic Link",
			"options": "holder_type",
			"width": 180,
		},
		{
			"label": _("Licence"),
			"fieldname": "item_type",
			"fieldtype": "Link",
			"options": "Compliance Item Type",
			"width": 170,
		},
		{"label": _("Number"), "fieldname": "reference_number", "fieldtype": "Data", "width": 160},
		{"label": _("Valid Until"), "fieldname": "valid_until", "fieldtype": "Date", "width": 100},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 140},
		{
			"label": _("Item"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Compliance Item",
			"width": 130,
		},
	]


def get_data(filters: frappe._dict):
	conditions = {"holder_type": filters.get("holder_type") or ("in", ["Customer", "Supplier"])}
	for field in ("holder", "item_type", "status"):
		if filters.get(field):
			conditions[field] = filters[field]
	return frappe.get_list(
		"Compliance Item",
		filters=conditions,
		fields=[column["fieldname"] for column in get_columns()],
		order_by="valid_until asc",
	)
