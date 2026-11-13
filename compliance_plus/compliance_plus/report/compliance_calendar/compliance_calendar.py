# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_first_day, get_last_day, getdate, nowdate


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{
			"label": _("Task"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Compliance Task",
			"width": 130,
		},
		{"label": _("Due"), "fieldname": "effective_due_date", "fieldtype": "Date", "width": 100},
		{
			"label": _("Obligation"),
			"fieldname": "obligation_template",
			"fieldtype": "Link",
			"options": "Compliance Obligation Template",
			"width": 220,
		},
		{"label": _("Law"), "fieldname": "law", "fieldtype": "Data", "width": 120},
		{"label": _("Period"), "fieldname": "period_label", "fieldtype": "Data", "width": 110},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 160,
		},
		{"label": _("Registration"), "fieldname": "registration_number", "fieldtype": "Data", "width": 140},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": _("Overdue"), "fieldname": "is_overdue", "fieldtype": "Check", "width": 80},
		{"label": _("Filed On"), "fieldname": "filed_on", "fieldtype": "Date", "width": 100},
		{
			"label": _("Acknowledgement"),
			"fieldname": "acknowledgement_number",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Responsible"),
			"fieldname": "responsible",
			"fieldtype": "Link",
			"options": "User",
			"width": 160,
		},
	]


def get_data(filters: frappe._dict):
	month = getdate(filters.get("month") or nowdate())
	conditions = {"effective_due_date": ("between", [get_first_day(month), get_last_day(month)])}
	for field in ("company", "law", "status", "responsible"):
		if filters.get(field):
			conditions[field] = filters[field]
	return frappe.get_list(
		"Compliance Task",
		filters=conditions,
		fields=[column["fieldname"] for column in get_columns()],
		order_by="effective_due_date asc",
	)
