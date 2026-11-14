# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from kxcompliance.kx_compliance.client_reports import companies_by_client, financial_year, summarise
from kxcompliance.kx_compliance.score import company_scores, worst


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	if not (filters.from_date and filters.to_date):
		filters.from_date, filters.to_date = financial_year()
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{
			"label": _("Client"),
			"fieldname": "client",
			"fieldtype": "Link",
			"options": "Compliance Client",
			"width": 200,
		},
		{"label": _("Companies"), "fieldname": "companies", "fieldtype": "Int", "width": 100},
		{"label": _("Filed On Time"), "fieldname": "on_time", "fieldtype": "Int", "width": 110},
		{"label": _("Filed Late"), "fieldname": "late", "fieldtype": "Int", "width": 100},
		{"label": _("Overdue"), "fieldname": "overdue", "fieldtype": "Int", "width": 90},
		{"label": _("On Time %"), "fieldname": "on_time_percent", "fieldtype": "Percent", "width": 100},
		{"label": _("Late Fees"), "fieldname": "late_fee", "fieldtype": "Currency", "width": 110},
		{"label": _("Interest"), "fieldname": "interest", "fieldtype": "Currency", "width": 110},
		{"label": _("Open Notices and Cases"), "fieldname": "open_cases", "fieldtype": "Int", "width": 120},
		{
			"label": _("Documents Awaited"),
			"fieldname": "waiting_on_client",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": _("DSCs Expired or Expiring"),
			"fieldname": "dscs_expiring",
			"fieldtype": "Int",
			"width": 120,
		},
		{"label": _("Lowest Score"), "fieldname": "lowest_score", "fieldtype": "Int", "width": 110},
		{
			"label": _("Late Fees Building Up"),
			"fieldname": "late_fees_so_far",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Relationship Manager"),
			"fieldname": "relationship_manager",
			"fieldtype": "Link",
			"options": "User",
			"width": 160,
		},
	]


def get_data(filters: frappe._dict) -> list[dict]:
	conditions = {"status": ("!=", "Left")}
	if filters.client:
		conditions["name"] = filters.client
	if filters.relationship_manager:
		conditions["relationship_manager"] = filters.relationship_manager
	clients = frappe.get_list(
		"Compliance Client", filters=conditions, fields=["name", "relationship_manager"], order_by="name asc"
	)
	totals = summarise([row.name for row in clients], filters.from_date, filters.to_date)
	client_of = companies_by_client([row.name for row in clients])
	scores = company_scores(list(client_of))
	rows = []
	for row in clients:
		companies = [company for company, client in client_of.items() if client == row.name]
		lowest = worst(scores, companies)
		rows.append(
			{
				"client": row.name,
				"relationship_manager": row.relationship_manager,
				**totals[row.name],
				"lowest_score": lowest["score"] if lowest else None,
				"late_fees_so_far": sum(scores[company]["late_fees_so_far"] for company in companies),
			}
		)
	# The clients that need the firm most come first: overdue filings, then the lowest on-time rate.
	return sorted(
		rows,
		key=lambda row: (
			-row["overdue"],
			row["on_time_percent"] if row["on_time_percent"] is not None else 101,
			row["client"],
		),
	)
