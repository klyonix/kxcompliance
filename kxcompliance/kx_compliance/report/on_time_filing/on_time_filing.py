# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from kxcompliance.kx_compliance.client_reports import companies_by_client

# A CA/CS firm also sees it per client, through the client's companies.
GROUPINGS = {"Company": "company", "Client": "company", "Law": "law", "Responsible": "responsible"}


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	group_by = filters.get("group_by") if filters.get("group_by") in GROUPINGS else "Company"
	return get_columns(group_by), get_data(filters, group_by)


def get_columns(group_by: str):
	return [
		{"label": _(group_by), "fieldname": "group", "fieldtype": "Data", "width": 200},
		{"label": _("Filed On Time"), "fieldname": "on_time", "fieldtype": "Int", "width": 120},
		{"label": _("Filed Late"), "fieldname": "late", "fieldtype": "Int", "width": 100},
		{"label": _("Overdue"), "fieldname": "overdue", "fieldtype": "Int", "width": 100},
		{"label": _("On Time %"), "fieldname": "on_time_percent", "fieldtype": "Percent", "width": 100},
		{"label": _("Late Fees"), "fieldname": "late_fee", "fieldtype": "Currency", "width": 120},
		{"label": _("Interest"), "fieldname": "interest", "fieldtype": "Currency", "width": 120},
	]


def get_data(filters: frappe._dict, group_by: str):
	group_field = GROUPINGS[group_by]
	conditions = {}
	if filters.get("company"):
		conditions["company"] = filters.company
	client_of = {}
	if group_by == "Client" or filters.get("client"):
		clients = frappe.get_list(
			"Compliance Client",
			filters={"name": filters.client} if filters.get("client") else {},
			fields=["name", "client_name"],
		)
		titles = {row.name: row.client_name or row.name for row in clients}
		# Each company's client as people see it: the group shown is the client's title.
		client_of = {company: titles[client] for company, client in companies_by_client(list(titles)).items()}
	if filters.get("client"):
		companies = list(client_of)
		if filters.get("company"):
			# Both filters: the company, if it is the client's.
			companies = [company for company in companies if company == filters.company]
		conditions["company"] = ("in", companies or [""])
	if filters.get("from_date") and filters.get("to_date"):
		conditions["effective_due_date"] = ("between", [filters.from_date, filters.to_date])
	tasks = frappe.get_list(
		"Compliance Task",
		filters=conditions,
		fields=[group_field, "status", "is_overdue", "late_fee", "interest"],
	)
	rows: dict[str, frappe._dict] = {}
	for task in tasks:
		if group_by == "Client":
			key = client_of.get(task.company) or _("No client")
		else:
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
