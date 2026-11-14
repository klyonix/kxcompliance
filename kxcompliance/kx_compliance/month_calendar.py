# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""What falls on each day of a month, for the app's calendar: filings on their due dates, register
items on the day they expire, hearings and other legal dates, and the dates documents are due from
clients. Everything is read with the person's own permissions, so each sees what they may see.
"""

import frappe
from frappe import _
from frappe.utils import date_diff, getdate

from kxcompliance.kx_compliance.overview import PARTY_HOLDERS

# A month grid shows at most six weeks; a little more leaves room without allowing a year at once.
MAX_DAYS = 45
LIMIT = 1000
FILED = ("Filed", "Filed Late")


def month_events(start: str, end: str, companies: list[str] | None = None) -> list[dict]:
	start, end = getdate(start), getdate(end)
	if not 0 <= date_diff(end, start) <= MAX_DAYS:
		frappe.throw(
			_("The calendar shows up to {0} days at a time, not {1} to {2}.").format(MAX_DAYS, start, end)
		)
	by_company = {"company": ("in", companies)} if companies is not None else {}
	return sorted(
		filings(start, end, by_company)
		+ expiries(start, end, by_company)
		+ legal_dates(start, end, by_company)
		+ requests(start, end, by_company),
		key=lambda event: (event["date"], event.get("time") or "", event["kind"], event["title"]),
	)


def filings(start, end, by_company: dict) -> list[dict]:
	rows = frappe.get_list(
		"Compliance Task",
		filters={
			"effective_due_date": ("between", [start, end]),
			"status": ("not in", ["Not Applicable", "Cancelled"]),
			**by_company,
		},
		fields=[
			"name",
			"obligation_template",
			"period_label",
			"company",
			"status",
			"is_overdue",
			"effective_due_date",
		],
		limit=LIMIT,
	)
	return [
		{
			"kind": "filing",
			"name": row.name,
			"date": str(row.effective_due_date),
			"title": row.obligation_template,
			"detail": " · ".join(filter(None, [row.period_label, row.company])),
			"status": row.status,
			"done": row.status in FILED,
			"overdue": bool(row.is_overdue),
		}
		for row in rows
	]


def expiries(start, end, by_company: dict) -> list[dict]:
	rows = frappe.get_list(
		"Compliance Item",
		filters={
			"valid_until": ("between", [start, end]),
			"is_cancelled": 0,
			"holder_type": ("not in", PARTY_HOLDERS),
			**by_company,
		},
		fields=["name", "title", "item_type", "company", "status", "valid_until"],
		limit=LIMIT,
	)
	return [
		{
			"kind": "licence",
			"name": row.name,
			"date": str(row.valid_until),
			"title": row.title,
			"detail": " · ".join(filter(None, [row.item_type, row.company])),
			"status": row.status,
			# Renewed means a new validity was recorded, which moves the item off this day.
			"done": False,
			"overdue": row.status in ("Expired", "Lapsed"),
		}
		for row in rows
	]


def legal_dates(start, end, by_company: dict) -> list[dict]:
	rows = frappe.get_list(
		"Legal Date",
		filters={"date": ("between", [start, end]), "status": ("!=", "Cancelled"), **by_company},
		fields=[
			"name",
			"kind",
			"date",
			"time",
			"status",
			"reference_doctype",
			"reference_name",
			"reference_title",
			"company",
		],
		limit=LIMIT,
	)
	return [
		{
			"kind": "legal",
			"name": row.name,
			"date": str(row.date),
			"time": str(row.time)[:5] if row.time else None,
			"title": f"{_(row.kind)}: {row.reference_title or row.reference_name}",
			"detail": row.company,
			"status": row.status,
			"done": row.status == "Done",
			"overdue": row.status == "Missed",
			"reference_doctype": row.reference_doctype,
			"reference_name": row.reference_name,
		}
		for row in rows
	]


def requests(start, end, by_company: dict) -> list[dict]:
	rows = frappe.get_list(
		"Document Request",
		filters={"due_date": ("between", [start, end]), "status": ("!=", "Withdrawn"), **by_company},
		fields=["name", "title", "company", "status", "due_date"],
		limit=LIMIT,
	)
	return [
		{
			"kind": "request",
			"name": row.name,
			"date": str(row.due_date),
			"title": row.title,
			"detail": row.company,
			"status": row.status,
			"done": row.status == "Accepted",
			"overdue": False,
		}
		for row in rows
	]
