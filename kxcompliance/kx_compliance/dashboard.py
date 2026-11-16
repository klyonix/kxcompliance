# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""The Overview's dashboard (RK, 15 Nov 2026): what is late and what falls due soon across
filings, licences and legal dates; what falls due month by month; how filings were filed month
by month; and what changed lately.

Counts are read with get_list, grouped by date in the query, so they respect the person's
permissions and cost one query per kind of record; months are summed from those groups here.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, get_first_day, getdate

from kxcompliance import scoped
from kxcompliance.kx_compliance.register import CLOSED_TASK_STATUSES

COUNT = {"COUNT": "*", "as": "count"}
SOON_DAYS = 7
MONTH_DAYS = 30
MONTHS_AHEAD = 6
MONTHS_BACK = 6
RECENT_LIMIT = 12
PARTY_HOLDERS = ["Customer", "Supplier"]
# Items whose renewal is nobody's yet; one planned or applied for is in hand.
UNHANDLED_ITEM_STATUSES = ["Active", "Due for Renewal", "Expired", "Lapsed"]
FILED = ("Filed", "Filed Late")
# Where the activity feed looks, and the field that names each record.
FEED_TITLES = {
	"Compliance Item": "title",
	"Compliance Task": "obligation_template",
	"Legal Case": "title",
	"Trademark": "mark",
	"Document Request": "title",
}


# Where each record keeps its company, to narrow the overview to one client's companies.
COMPANY_FIELDS = {
	"Compliance Item": "company",
	"Compliance Task": "company",
	"Legal Date": "company",
	"Legal Case": "company",
	"Trademark": "applicant",
	"Document Request": "company",
}


def within(doctype: str, filters: dict | list | None, companies: list[str] | None):
	"""The filters, narrowed to these companies; None is every company. Records with no company
	(licence checks, privacy) are the firm's own and stay as they are."""
	field = COMPANY_FIELDS.get(doctype)
	if companies is None or not field:
		return filters or {}
	# No company at all narrows to nothing, as a client with no companies yet should.
	wanted = list(companies) or [""]
	if isinstance(filters, list):
		return [*filters, [field, "in", wanted]]
	return {**(filters or {}), field: ("in", wanted)}


def by_date(doctype: str, date_field: str, filters: dict, companies: list[str] | None = None) -> list[dict]:
	"""How many records fall on each date, as [{date, count}]."""
	rows = frappe.get_list(
		doctype,
		filters=within(doctype, filters, companies),
		fields=[f"{date_field} as date", COUNT],
		group_by=date_field,
		order_by=None,
	)
	return [{"date": getdate(row.date), "count": row["count"]} for row in rows if row.date]


def sum_between(rows: list[dict], start, end) -> int:
	return sum(row["count"] for row in rows if start <= row["date"] <= end)


def urgency(today, companies: list[str] | None = None) -> list[dict]:
	"""Late, due this week and due later in the month, across filings, own licences and legal
	dates; each split by kind, with the filters that list exactly what it counts."""
	week, month = add_days(today, SOON_DAYS), add_days(today, MONTH_DAYS)
	kinds = [
		(
			_("Filings"),
			"Compliance Task",
			"effective_due_date",
			[["status", "not in", list(CLOSED_TASK_STATUSES)]],
		),
		(
			_("Renewals"),
			"Compliance Item",
			"valid_until",
			[
				["status", "in", UNHANDLED_ITEM_STATUSES],
				["holder_type", "not in", PARTY_HOLDERS],
				["is_cancelled", "=", 0],
			],
		),
		(_("Legal dates"), "Legal Date", "date", [["status", "=", "Scheduled"]]),
	]
	spans = [
		("overdue", _("Overdue"), [["<", str(today)]]),
		("week", _("Due this week"), [["between", [str(today), str(week)]]]),
		("month", _("Due in 30 days"), [["between", [str(add_days(week, 1)), str(month)]]]),
	]
	counted = {
		label: by_date(doctype, field, {row[0]: (row[1], row[2]) for row in base}, companies)
		for label, doctype, field, base in kinds
	}
	long_ago = getdate("1900-01-01")
	bounds = {
		"overdue": (long_ago, add_days(today, -1)),
		"week": (today, week),
		"month": (add_days(week, 1), month),
	}
	tiles = []
	for key, title, (span,) in spans:
		parts = []
		for label, doctype, field, base in kinds:
			start, end = bounds[key]
			parts.append(
				{
					"label": label,
					"value": sum_between(counted[label], start, end),
					"doctype": doctype,
					"filters": [*base, [field, *span]],
				}
			)
		tiles.append(
			{"key": key, "label": title, "value": sum(part["value"] for part in parts), "parts": parts}
		)
	review = frappe.get_list(
		"Compliance Task",
		filters=within("Compliance Task", {"status": "Ready for Review"}, companies),
		fields=[COUNT],
	)[0]["count"]
	tiles.append(
		{
			"key": "review",
			"label": _("Waiting for review"),
			"value": review,
			"parts": [
				{
					"label": _("Filings"),
					"value": review,
					"doctype": "Compliance Task",
					"filters": [["status", "=", "Ready for Review"]],
				}
			],
		}
	)
	return tiles


def month_starts(first, count: int) -> list:
	return [add_months(first, step) for step in range(count)]


def due_by_month(today, companies: list[str] | None = None) -> list[dict]:
	"""What falls due in each of the next months: filings, licence renewals and legal dates."""
	first = get_first_day(today)
	end = add_days(add_months(first, MONTHS_AHEAD), -1)
	window = ("between", [first, end])
	tasks = by_date(
		"Compliance Task",
		"effective_due_date",
		{"status": ("not in", CLOSED_TASK_STATUSES), "effective_due_date": window},
		companies,
	)
	items = by_date(
		"Compliance Item",
		"valid_until",
		{"is_cancelled": 0, "holder_type": ("not in", PARTY_HOLDERS), "valid_until": window},
		companies,
	)
	dates = by_date("Legal Date", "date", {"status": "Scheduled", "date": window}, companies)
	months = []
	for start in month_starts(first, MONTHS_AHEAD):
		stop = add_days(add_months(start, 1), -1)
		months.append(
			{
				"month": start.strftime("%b %Y"),
				_("Filings"): sum_between(tasks, start, stop),
				_("Renewals"): sum_between(items, start, stop),
				_("Legal dates"): sum_between(dates, start, stop),
			}
		)
	return months


def filed_by_month(today, companies: list[str] | None = None) -> list[dict]:
	"""Filings that fell due in each of the last months: filed on time, filed late, still open."""
	first = add_months(get_first_day(today), -(MONTHS_BACK - 1))
	window = ("between", [first, today])
	rows = frappe.get_list(
		"Compliance Task",
		filters=within(
			"Compliance Task",
			{"effective_due_date": window, "status": ("not in", ["Not Applicable", "Cancelled"])},
			companies,
		),
		fields=["effective_due_date as date", "status", COUNT],
		group_by="effective_due_date, status",
		order_by=None,
	)
	months = []
	for start in month_starts(first, MONTHS_BACK):
		stop = add_days(add_months(start, 1), -1)
		inside = [row for row in rows if row.date and start <= getdate(row.date) <= stop]

		def counted(statuses, rows=inside):
			return sum(row["count"] for row in rows if row.status in statuses)

		months.append(
			{
				"month": start.strftime("%b %Y"),
				_("On time"): counted(("Filed",)),
				_("Late"): counted(("Filed Late",)),
				_("Not filed"): counted(("Open", "In Progress", "Ready for Review")),
			}
		)
	return months


def recent_activity(companies: list[str] | None = None) -> list[dict]:
	"""The latest changes to filings, licences, cases, trademarks and document requests, with
	who made them. Only what the person may read: each record's title is read with get_list."""
	# Only System Managers read Version, so the who-and-when is read here; what is shown is limited
	# to records the person may read, as each title below is read with get_list.
	versions = scoped.get_all(
		"Version",
		filters={"ref_doctype": ("in", list(FEED_TITLES))},
		fields=["ref_doctype", "docname", "owner", "creation"],
		order_by="creation desc",
		limit=RECENT_LIMIT * 3,
	)
	by_type: dict[str, set[str]] = {}
	for version in versions:
		by_type.setdefault(version.ref_doctype, set()).add(version.docname)
	titles = {}
	for doctype, names in by_type.items():
		for row in frappe.get_list(
			doctype,
			filters=within(doctype, {"name": ("in", list(names))}, companies),
			fields=["name", f"{FEED_TITLES[doctype]} as title"],
			limit=len(names),
		):
			titles[(doctype, row.name)] = row.title or row.name
	feed, seen = [], set()
	for version in versions:
		key = (version.ref_doctype, version.docname)
		# A record the person may not read is left out; one changed twice shows once.
		if key not in titles or key in seen:
			continue
		seen.add(key)
		feed.append(
			{
				"doctype": version.ref_doctype,
				"name": version.docname,
				"title": titles[key],
				"by": version.owner,
				"on": str(version.creation),
			}
		)
		if len(feed) == RECENT_LIMIT:
			break
	return feed


def get_dashboard(today, companies: list[str] | None = None) -> dict:
	today = getdate(today)
	return {
		"urgency": urgency(today, companies),
		"due_by_month": due_by_month(today, companies),
		"filed_by_month": filed_by_month(today, companies),
		"recent": recent_activity(companies),
	}
