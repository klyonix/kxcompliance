# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

GROUPINGS = {"Company": "company", "Law": "law", "Responsible": "responsible"}


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	group_field = GROUPINGS.get(filters.get("group_by") or "Company", "company")
	return get_columns(group_field), get_data(filters, group_field)


def get_columns(group_field: str):
	return [
		{"label": _(group_field.title()), "fieldname": "group", "fieldtype": "Data", "width": 200},
		{"label": _("Filed On Time"), "fieldname": "on_time", "fieldtype": "Int", "width": 120},
		{"label": _("Filed Late"), "fieldname": "late", "fieldtype": "Int", "width": 100},
		{"label": _("Overdue"), "fieldname": "overdue", "fieldtype": "Int", "width": 100},
		{"label": _("On Time %"), "fieldname": "on_time_percent", "fieldtype": "Percent", "width": 100},
		{"label": _("Late Fees"), "fieldname": "late_fee", "fieldtype": "Currency", "width": 120},
		{"label": _("Interest"), "fieldname": "interest", "fieldtype": "Currency", "width": 120},
	]


def get_data(filters: frappe._dict, group_field: str):
	conditions = {}
	if filters.get("company"):
		conditions["company"] = filters.company
	if filters.get("from_date") and filters.get("to_date"):
		conditions["effective_due_date"] = ("between", [filters.from_date, filters.to_date])
	tasks = frappe.get_list(
		"Compliance Task",
		filters=conditions,
		fields=[group_field, "status", "is_overdue", "late_fee", "interest"],
	)
	rows: dict[str, frappe._dict] = {}
	for task in tasks:
		key = task.get(group_field) or _("Not set")
		row = rows.setdefault(
			key, frappe._dict(group=key, on_time=0, late=0, overdue=0, late_fee=0, interest=0)
		)
		if task.status == "Filed":
			row.on_time += 1
		elif task.status == "Filed Late":
			row.late += 1
		elif task.is_overdue:
			row.overdue += 1
		row.late_fee += flt(task.late_fee)
		row.interest += flt(task.interest)
	for row in rows.values():
		counted = row.on_time + row.late + row.overdue
		row.on_time_percent = flt(row.on_time * 100 / counted, 1) if counted else 0
	return sorted(rows.values(), key=lambda row: row.on_time_percent)
