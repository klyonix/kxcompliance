# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""The compliance score of a company, and what filing late costs.

The score starts at 100 and loses points for what needs fixing: each overdue filing, expired
licence or DSC, filing done late in the last twelve months, item due for renewal and not yet
applied for, and open notice or case (more for a probable liability). It never goes below 0,
and comes with its reasons so people see what to fix.

A filing's late fee is worked out from its obligation template's figures (penalty_library.py):
a one-off fee and a fee per day, up to a cap and, where the law says so, up to the tax. Interest
needs the tax amount, which the app knows only once it is paid, so for an unpaid filing the
rate is given instead.

Scores count everything in the company, whoever holds it: callers show them only to people who
may see the company (managers, the client's team, the client's own logins).
"""

import frappe
from frappe import _
from frappe.utils import add_months, date_diff, flt, getdate, nowdate

from kxcompliance import scoped
from kxcompliance.kx_compliance.overview import OPEN_CASE_STATUSES, PARTY_HOLDERS
from kxcompliance.kx_compliance.penalty_figures import firm_figures
from kxcompliance.kx_compliance.penalty_library import FIELDS as PENALTY_FIELDS
from kxcompliance.kx_compliance.penalty_library import NIL_FIELDS
from kxcompliance.kx_compliance.register import CLOSED_TASK_STATUSES

FULL_SCORE = 100
POINTS = {
	"overdue": 10,
	# Nothing to report, but still late: the law charges a smaller fee, and so does the score.
	"overdue_nil": 3,
	# Past its last day to file: filing can no longer put it right (RK, 21 Nov 2026).
	"time_barred": 15,
	"expired": 10,
	"filed_late": 2,
	"due_for_renewal": 3,
	"open_case": 5,
	"probable_case": 10,
}
RULE_FIELDS = [
	"name",
	"late_fee_per_day",
	"late_fee_flat",
	"late_fee_cap",
	"cap_at_tax",
	"interest_percent",
	"penalty_rule",
	"penalty_checked_on",
	"allows_nil",
	*NIL_FIELDS,
]
COUNT = {"COUNT": "*", "as": "count"}


def nil_figures(rules) -> frappe._dict:
	"""The template's figures for a late NIL return, in the shape late_fee reads. There is no tax,
	so no interest either."""
	return frappe._dict(
		rules,
		late_fee_flat=rules.nil_late_fee_flat,
		late_fee_per_day=rules.nil_late_fee_per_day,
		late_fee_cap=rules.nil_late_fee_cap,
		cap_at_tax=0,
		interest_percent=0,
	)


def fee_figures(rules, is_nil: bool = False):
	"""The figures a filing's late fee is worked out from: the NIL ones for a NIL return."""
	if rules and is_nil and rules.allows_nil:
		return nil_figures(rules)
	return rules


def late_fee(rules, days_late: int, tax: float | None = None) -> float:
	"""The late fee after `days_late` days, by the template's figures (see fee_figures)."""
	if not rules or days_late <= 0:
		return 0.0
	fee = flt(rules.late_fee_flat) + flt(rules.late_fee_per_day) * days_late
	if flt(rules.late_fee_cap):
		fee = min(fee, flt(rules.late_fee_cap))
	if rules.cap_at_tax and flt(tax):
		fee = min(fee, flt(tax))
	return flt(fee, 2)


def rules_for(templates: list[str]) -> dict[str, frappe._dict]:
	"""Each obligation's late-filing figures: the firm's own where it has set them, else the
	obligation's (for a standard one, the library's)."""
	if not templates:
		return {}
	rows = scoped.get_all(
		"Compliance Obligation Template", filters={"name": ("in", list(set(templates)))}, fields=RULE_FIELDS
	)
	own = firm_figures(row.name for row in rows)
	for row in rows:
		row.penalty_set_by_firm = row.name in own
		if row.penalty_set_by_firm:
			row.update({field: own[row.name].get(field) for field in PENALTY_FIELDS})
	return {row.name: row for row in rows}


def filing_penalty(task, today: str | None = None) -> dict:
	"""What a filing's lateness costs, or would cost: so far, in a week, and the rule behind it."""
	today = getdate(today or nowdate())
	rules = fee_figures(rules_for([task.obligation_template]).get(task.obligation_template), task.is_nil)
	due = getdate(task.effective_due_date)
	filed = task.status in ("Filed", "Filed Late") and task.filed_on
	days_late = date_diff(task.filed_on if filed else today, due)
	counted = bool(rules and (flt(rules.late_fee_per_day) or flt(rules.late_fee_flat)))
	return {
		"days_late": max(days_late, 0),
		"days_left": max(-days_late, 0) if not filed else 0,
		"late_fee": late_fee(rules, days_late, task.amount_paid),
		# A week from today: still nothing if it is due more than a week away.
		"late_fee_in_a_week": None if filed else late_fee(rules, days_late + 7, task.amount_paid),
		"late_fee_paid": flt(task.late_fee),
		"interest_percent": flt(rules.interest_percent) if rules else 0,
		"counted": counted,
		"rule": rules.penalty_rule if rules else None,
		"checked_on": str(rules.penalty_checked_on) if rules and rules.penalty_checked_on else None,
		"set_by_firm": bool(rules and rules.penalty_set_by_firm),
		"nil": bool(rules and task.is_nil and rules.allows_nil),
	}


def company_scores(companies: list[str], today: str | None = None) -> dict[str, dict]:
	"""Each company's score, its reasons, and the late fees its overdue filings have run up."""
	today = getdate(today or nowdate())
	counts = {company: dict.fromkeys(POINTS, 0) for company in companies}
	penalty = dict.fromkeys(companies, 0.0)
	if not companies:
		return {}

	overdue = scoped.get_all(
		"Compliance Task",
		filters={"company": ("in", companies), "status": ("not in", CLOSED_TASK_STATUSES), "is_overdue": 1},
		fields=[
			"company",
			"obligation_template",
			"effective_due_date",
			"amount_paid",
			"is_nil",
			"is_time_barred",
		],
	)
	rules = rules_for([row.obligation_template for row in overdue])
	for row in overdue:
		counts[row.company][overdue_kind(row)] += 1
		days_late = date_diff(today, getdate(row.effective_due_date))
		figures = fee_figures(rules.get(row.obligation_template), row.is_nil)
		penalty[row.company] += late_fee(figures, days_late, row.amount_paid)

	for row in scoped.get_all(
		"Compliance Task",
		filters={
			"company": ("in", companies),
			"status": "Filed Late",
			"effective_due_date": ("between", [add_months(today, -12), today]),
		},
		fields=["company", COUNT],
		group_by="company",
	):
		counts[row.company]["filed_late"] = row["count"]

	for row in scoped.get_all(
		"Compliance Item",
		filters={
			"company": ("in", companies),
			"is_cancelled": 0,
			"holder_type": ("not in", PARTY_HOLDERS),
			# A planned renewal is still due: planning alone does not raise the score.
			"status": ("in", ["Expired", "Lapsed", "Due for Renewal", "Renewal Planned"]),
		},
		fields=["company", "status", COUNT],
		group_by="company, status",
	):
		key = "due_for_renewal" if row.status in ("Due for Renewal", "Renewal Planned") else "expired"
		counts[row.company][key] += row["count"]

	for row in scoped.get_all(
		"Legal Case",
		filters={"company": ("in", companies), "status": ("in", OPEN_CASE_STATUSES)},
		fields=["company", "risk", COUNT],
		group_by="company, risk",
	):
		key = "probable_case" if row.risk == "Probable" else "open_case"
		counts[row.company][key] += row["count"]

	return {
		company: {
			"score": max(FULL_SCORE - sum(POINTS[key] * count for key, count in counts[company].items()), 0),
			"reasons": reasons(counts[company]),
			"late_fees_so_far": flt(penalty[company], 2),
		}
		for company in companies
	}


def overdue_kind(row) -> str:
	"""Which of the score's reasons an overdue filing counts under."""
	if row.is_time_barred:
		return "time_barred"
	return "overdue_nil" if row.is_nil else "overdue"


def reason_label(key: str, count: int) -> str:
	one = count == 1
	labels = {
		"overdue": _("{0} filing overdue") if one else _("{0} filings overdue"),
		"overdue_nil": _("{0} NIL return overdue") if one else _("{0} NIL returns overdue"),
		"time_barred": _("{0} filing time-barred") if one else _("{0} filings time-barred"),
		"expired": _("{0} licence or certificate expired")
		if one
		else _("{0} licences or certificates expired"),
		"filed_late": _("{0} filing done late this year") if one else _("{0} filings done late this year"),
		"due_for_renewal": _("{0} item due for renewal") if one else _("{0} items due for renewal"),
		"open_case": _("{0} open notice or case") if one else _("{0} open notices or cases"),
		"probable_case": _("{0} probable liability") if one else _("{0} probable liabilities"),
	}
	return labels[key].format(count)


def reasons(counts: dict[str, int]) -> list[dict]:
	"""What took points off, the biggest first."""
	found = [
		{
			"key": key,
			"label": reason_label(key, count),
			"points": -POINTS[key] * count,
		}
		for key, count in counts.items()
		if count
	]
	return sorted(found, key=lambda reason: reason["points"])


def worst(scores: dict[str, dict], companies: list[str]) -> dict | None:
	"""The lowest-scoring of the companies, with its score: a client is as sound as its weakest."""
	known = [(scores[company]["score"], company) for company in companies if company in scores]
	if not known:
		return None
	score, company = min(known)
	return {"score": score, "company": company}
