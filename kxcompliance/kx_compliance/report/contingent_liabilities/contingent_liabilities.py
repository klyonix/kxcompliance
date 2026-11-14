# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, nowdate


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Case"), "fieldname": "name", "fieldtype": "Link", "options": "Legal Case", "width": 130},
		{"label": _("Title"), "fieldname": "title", "fieldtype": "Data", "width": 240},
		{"label": _("Forum"), "fieldname": "forum", "fieldtype": "Data", "width": 140},
		{"label": _("Opposing Party"), "fieldname": "opposing_party", "fieldtype": "Data", "width": 160},
		{"label": _("Risk"), "fieldname": "risk", "fieldtype": "Data", "width": 90},
		{
			"label": _("Amount Involved"),
			"fieldname": "amount_involved",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140,
		},
		{
			"label": _("Provision"),
			"fieldname": "provision",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"label": _("Not Provided For"),
			"fieldname": "not_provided",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140,
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
	"""Cases open on the chosen date: filed by then and not closed before it."""
	as_at = getdate(filters.get("as_at") or nowdate())
	conditions = {"filing_date": ("<=", as_at), "amount_involved": (">", 0)}
	if filters.get("company"):
		conditions["company"] = filters.company
	cases = frappe.get_list(
		"Legal Case",
		filters=conditions,
		or_filters=[["closed_on", "is", "not set"], ["closed_on", ">", as_at]],
		fields=[
			"name",
			"title",
			"forum",
			"opposing_party",
			"risk",
			"amount_involved",
			"provision",
			"currency",
			"closed_on",
		],
		order_by="risk asc, amount_involved desc",
	)
	for case in cases:
		case.not_provided = (case.amount_involved or 0) - (case.provision or 0)
	return cases
