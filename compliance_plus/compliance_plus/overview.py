# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""The managers' overview in the app: the workspace's numbers, and the on-time filing rate.

Counts are grouped by doctype in a few queries rather than one per number, read with
get_list so they respect the person's permissions, and each number links to the Desk
list behind it with the same filters.
"""

import json
from urllib.parse import quote, urlencode

import frappe
from frappe import _
from frappe.utils import add_days, add_months, nowdate

from compliance_plus.compliance_plus.register import CLOSED_TASK_STATUSES

COUNT = {"COUNT": "*", "as": "count"}
PARTY_HOLDERS = ["Customer", "Supplier"]
OPEN_CASE_STATUSES = ["Open", "Stayed", "Reserved for Order"]
PENDING_MARK_STATUSES = [
	"New Application",
	"Formalities Check Pass",
	"Marked for Exam",
	"Objected",
	"Accepted and Advertised",
	"Opposed",
]
ON_TIME_MONTHS = 12
ON_TIME_REPORT = "On-time Filing"


def grouped_counts(doctype: str, group_by: list[str], filters: dict | None = None) -> list[dict]:
	return frappe.get_list(
		doctype,
		filters=filters or {},
		fields=[*group_by, COUNT],
		group_by=", ".join(group_by),
		order_by=None,
	)


def total(rows: list[dict], **match) -> int:
	return sum(
		row["count"]
		for row in rows
		if all(
			row.get(field) in wanted if isinstance(wanted, list | tuple | set) else row.get(field) == wanted
			for field, wanted in match.items()
		)
	)


def count(doctype: str, filters: dict) -> int:
	return frappe.get_list(doctype, filters=filters, fields=[COUNT])[0]["count"]


def desk_link(doctype: str, filters: dict) -> str:
	"""The Desk list of `doctype` with `filters`, which the list reads from its address."""
	query = {
		field: json.dumps(list(value)) if isinstance(value, list | tuple) else value
		for field, value in filters.items()
	}
	return f"/app/{frappe.scrub(doctype).replace('_', '-')}?{urlencode(query)}"


def card(label: str, value: int, tone: str, doctype: str, filters: dict) -> dict:
	return {"label": label, "value": value, "tone": tone, "link": desk_link(doctype, filters)}


def get_overview() -> dict:
	today = nowdate()
	week = ("between", [today, add_days(today, 7)])
	not_party = ("not in", PARTY_HOLDERS)
	is_party = ("in", PARTY_HOLDERS)

	items = grouped_counts("Compliance Item", ["status", "holder_type"])
	own = [row for row in items if row.holder_type not in PARTY_HOLDERS]
	parties = [row for row in items if row.holder_type in PARTY_HOLDERS]
	tasks = grouped_counts("Compliance Task", ["status", "is_overdue"])
	dates = grouped_counts("Legal Date", ["status", "is_overdue"])
	cases = grouped_counts("Legal Case", ["status", "risk"])
	marks = grouped_counts("Trademark", ["status"])

	expired = ["Expired", "Lapsed"]
	return {
		"sections": [
			{
				"title": _("Register"),
				"cards": [
					card(
						_("Due for renewal"),
						total(own, status="Due for Renewal"),
						"amber",
						"Compliance Item",
						{"status": "Due for Renewal", "holder_type": not_party},
					),
					card(
						_("Expired or lapsed"),
						total(own, status=expired),
						"red",
						"Compliance Item",
						{"status": ("in", expired), "holder_type": not_party},
					),
					card(
						_("Renewals in progress"),
						total(own, status="Renewal in Progress"),
						"blue",
						"Compliance Item",
						{"status": "Renewal in Progress", "holder_type": not_party},
					),
					card(
						_("Active"),
						total(own, status="Active"),
						"green",
						"Compliance Item",
						{"status": "Active", "holder_type": not_party},
					),
				],
			},
			{
				"title": _("Filings"),
				"cards": [
					card(
						_("Due this week"),
						count(
							"Compliance Task",
							{"status": ("not in", CLOSED_TASK_STATUSES), "effective_due_date": week},
						),
						"amber",
						"Compliance Task",
						{"status": ("not in", CLOSED_TASK_STATUSES), "effective_due_date": week},
					),
					card(
						_("Overdue"),
						total(tasks, is_overdue=1),
						"red",
						"Compliance Task",
						{"is_overdue": 1},
					),
					card(
						_("Waiting for review"),
						total(tasks, status="Ready for Review"),
						"blue",
						"Compliance Task",
						{"status": "Ready for Review"},
					),
					card(
						_("Filed late"),
						total(tasks, status="Filed Late"),
						"gray",
						"Compliance Task",
						{"status": "Filed Late"},
					),
				],
			},
			{
				"title": _("Legal"),
				"cards": [
					card(
						_("Hearings and deadlines this week"),
						count("Legal Date", {"status": "Scheduled", "date": week}),
						"blue",
						"Legal Date",
						{"status": "Scheduled", "date": week},
					),
					card(
						_("Outcomes not recorded"),
						total(dates, is_overdue=1),
						"red",
						"Legal Date",
						{"is_overdue": 1},
					),
					card(
						_("Open cases"),
						total(cases, status=OPEN_CASE_STATUSES),
						"gray",
						"Legal Case",
						{"status": ("in", OPEN_CASE_STATUSES)},
					),
					card(
						_("Probable liabilities"),
						total(cases, status=OPEN_CASE_STATUSES, risk="Probable"),
						"red",
						"Legal Case",
						{"status": ("in", OPEN_CASE_STATUSES), "risk": "Probable"},
					),
				],
			},
			{
				"title": _("Trademarks"),
				"cards": [
					card(
						_("Pending"),
						total(marks, status=PENDING_MARK_STATUSES),
						"blue",
						"Trademark",
						{"status": ("in", PENDING_MARK_STATUSES)},
					),
					card(
						_("Objected or opposed"),
						total(marks, status=["Objected", "Opposed"]),
						"amber",
						"Trademark",
						{"status": ("in", ["Objected", "Opposed"])},
					),
					card(
						_("Registered"),
						total(marks, status="Registered"),
						"green",
						"Trademark",
						{"status": "Registered"},
					),
				],
			},
			{
				"title": _("Customer and supplier licences"),
				"cards": [
					card(
						_("Due for renewal"),
						total(parties, status="Due for Renewal"),
						"amber",
						"Compliance Item",
						{"status": "Due for Renewal", "holder_type": is_party},
					),
					card(
						_("Expired"),
						total(parties, status=expired),
						"red",
						"Compliance Item",
						{"status": ("in", expired), "holder_type": is_party},
					),
					card(
						_("Sales and purchases blocked"),
						count("Licence Check Log", {"result": "Blocked"}),
						"red",
						"Licence Check Log",
						{"result": "Blocked"},
					),
				],
			},
		],
		"on_time": on_time_rate(today),
	}


def on_time_rate(today: str) -> dict:
	"""Filings due in the last twelve months: filed on time, filed late, and overdue."""
	since = add_months(today, -ON_TIME_MONTHS)
	rows = grouped_counts(
		"Compliance Task",
		["status", "is_overdue"],
		{"effective_due_date": ("between", [since, today])},
	)
	on_time = total(rows, status="Filed")
	late = total(rows, status="Filed Late")
	overdue = total(rows, is_overdue=1)
	counted = on_time + late + overdue
	return {
		"from_date": str(since),
		"to_date": str(today),
		"on_time": on_time,
		"late": late,
		"overdue": overdue,
		"percent": round(on_time * 100 / counted, 1) if counted else None,
		"link": f"/app/query-report/{quote(ON_TIME_REPORT)}?"
		+ urlencode({"from_date": str(since), "to_date": str(today)}),
	}
