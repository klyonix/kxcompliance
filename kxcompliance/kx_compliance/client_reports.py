# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""A CA/CS firm's numbers per client: how its filings went in a period, what it paid in late
fees and interest, and what is open now (notices and cases, documents the firm is waiting for,
DSCs about to expire).

Every count is read with get_list, grouped in the query, so each person sees only the clients
and records they may read, in a handful of queries however many clients there are.
"""

import frappe
from frappe.utils import add_days, add_months, flt, getdate, nowdate

from kxcompliance import scoped
from kxcompliance.kx_compliance.doctype.compliance_item.compliance_item import DSC_TYPE
from kxcompliance.kx_compliance.overview import OPEN_CASE_STATUSES
from kxcompliance.kx_compliance.register import TIME_BARRED

COUNT = {"COUNT": "*", "as": "count"}
DSC_WARNING_DAYS = 30
NUMBERS = (
	"on_time",
	"late",
	"overdue",
	"late_fee",
	"interest",
	"open_cases",
	"waiting_on_client",
	"dscs_expiring",
)


def financial_year(today: str | None = None) -> tuple[str, str]:
	"""The fiscal year set up in ERPNext for today, else April to March as in India."""
	from erpnext.accounts.utils import get_fiscal_year

	today = today or nowdate()
	year = get_fiscal_year(today, as_dict=True, raise_on_missing=False)
	if year:
		return str(year.year_start_date), str(year.year_end_date)
	day = getdate(today)
	start = getdate(f"{day.year if day.month >= 4 else day.year - 1}-04-01")
	return str(start), str(add_days(add_months(start, 12), -1))


def companies_by_client(clients: list[str]) -> dict[str, str]:
	"""Company → client, for the given clients."""
	if not clients:
		return {}
	# Only the link, for clients the caller has already read with get_list.
	rows = scoped.get_all(
		"Company Compliance Profile", filters={"client": ("in", clients)}, fields=["company", "client"]
	)
	return {row.company: row.client for row in rows}


def summarise(clients: list[str], from_date: str, to_date: str) -> dict[str, frappe._dict]:
	"""The numbers of each client, keyed by client name."""
	totals = {client: frappe._dict(dict.fromkeys(NUMBERS, 0), companies=0) for client in clients}
	client_of = companies_by_client(clients)
	for client in client_of.values():
		totals[client].companies += 1
	companies = list(client_of)
	if not companies:
		return totals
	add_filings(totals, client_of, companies, from_date, to_date)
	add_open_work(totals, client_of, companies, clients)
	for row in totals.values():
		counted = row.on_time + row.late + row.overdue
		row.on_time_percent = flt(row.on_time * 100 / counted, 1) if counted else None
	return totals


def add_filings(totals, client_of, companies, from_date, to_date):
	rows = frappe.get_list(
		"Compliance Task",
		filters={"company": ("in", companies), "effective_due_date": ("between", [from_date, to_date])},
		fields=[
			"company",
			"status",
			"is_overdue",
			COUNT,
			{"SUM": "late_fee", "as": "late_fee"},
			{"SUM": "interest", "as": "interest"},
		],
		group_by="company, status, is_overdue",
		order_by=None,
	)
	for row in rows:
		total = totals[client_of[row.company]]
		if row.status == "Filed":
			total.on_time += row["count"]
		elif row.status == "Filed Late":
			total.late += row["count"]
		elif row.is_overdue or row.status == TIME_BARRED:
			total.overdue += row["count"]
		total.late_fee += flt(row.late_fee)
		total.interest += flt(row.interest)


def add_open_work(totals, client_of, companies, clients):
	"""What is open today, whatever the period: it is what the firm has to act on now."""
	for row in frappe.get_list(
		"Legal Case",
		filters={"company": ("in", companies), "status": ("in", OPEN_CASE_STATUSES)},
		fields=["company", COUNT],
		group_by="company",
		order_by=None,
	):
		totals[client_of[row.company]].open_cases += row["count"]
	for row in frappe.get_list(
		"Document Request",
		filters={"client": ("in", clients), "status": "Requested"},
		fields=["client", COUNT],
		group_by="client",
		order_by=None,
	):
		totals[row.client].waiting_on_client += row["count"]
	for row in frappe.get_list(
		"Compliance Item",
		filters={
			"company": ("in", companies),
			"item_type": DSC_TYPE,
			"is_cancelled": 0,
			"valid_until": ("<=", add_days(nowdate(), DSC_WARNING_DAYS)),
		},
		fields=["company", COUNT],
		group_by="company",
		order_by=None,
	):
		totals[client_of[row.company]].dscs_expiring += row["count"]
