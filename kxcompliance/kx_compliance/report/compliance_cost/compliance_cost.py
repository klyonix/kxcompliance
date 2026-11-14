# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

CYCLES_PER_YEAR = {"Monthly": 12, "Quarterly": 4, "Yearly": 1, "One-time": 1, "": 1, None: 1}


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{
			"label": _("Type"),
			"fieldname": "item_type",
			"fieldtype": "Link",
			"options": "Compliance Item Type",
			"width": 200,
		},
		{
			"label": _("Supplier"),
			"fieldname": "supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 200,
		},
		{"label": _("Items"), "fieldname": "item_count", "fieldtype": "Int", "width": 80},
		{
			"label": _("Cost per Year"),
			"fieldname": "annual_cost",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"label": _("Currency"),
			"fieldname": "currency",
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		},
	]


def get_data(filters: frappe._dict):
	conditions = {"is_cancelled": 0}
	for field in ("company", "category"):
		if filters.get(field):
			conditions[field] = filters[field]
	items = frappe.get_list(
		"Compliance Item",
		filters=conditions,
		fields=["item_type", "supplier", "cost", "billing_cycle", "currency"],
	)
	totals: dict[tuple, frappe._dict] = {}
	for item in items:
		key = (item.item_type, item.supplier, item.currency)
		row = totals.setdefault(
			key,
			frappe._dict(
				item_type=item.item_type,
				supplier=item.supplier,
				currency=item.currency,
				item_count=0,
				annual_cost=0,
			),
		)
		row.item_count += 1
		row.annual_cost += flt(item.cost) * CYCLES_PER_YEAR.get(item.billing_cycle, 1)
	return sorted(totals.values(), key=lambda row: row.annual_cost, reverse=True)
