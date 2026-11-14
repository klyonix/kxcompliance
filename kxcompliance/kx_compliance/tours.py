# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Which of the app's tours each person has been shown (RK, 15 Nov 2026).

The tours themselves are in the front end (frontend/src/tours/tours.js); this only remembers who
has seen which, so a page's tour plays by itself the first time and is replayed on demand. Every
start is counted: the replays show where people still have doubts.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

VIEW = "Compliance Tour View"

# Every tour the app ships; tours.js must list the same ids, which test_tours holds.
TOURS = (
	"welcome",
	"overview",
	"calendar",
	"filings",
	"filing",
	"bulk-filing",
	"extensions",
	"register",
	"item",
	"signatories",
	"legal",
	"case",
	"trademark",
	"clients",
	"client",
	"client-home",
	"document-request",
	"bulk-setup",
	"settings",
	"people",
	"companies",
	"company",
	"obligations",
	"item-types",
	"licence-check",
	"licence-rules",
	"licence-blocks",
	"reports",
	"report",
	"help",
)


def seen() -> dict:
	user = frappe.session.user
	names = frappe.get_all(VIEW, filters={"user": user}, pluck="tour")
	return {"seen": sorted(set(names) & set(TOURS))}


def opened(tour: str) -> dict:
	"""This person started a tour; the first time marks it seen."""
	if tour not in TOURS:
		frappe.throw(_("There is no tour called {0}.").format(tour))
	user = frappe.session.user
	now = now_datetime()
	name = f"{user}:{tour}"
	times = frappe.db.get_value(VIEW, name, "times_opened")
	if times is not None:
		frappe.db.set_value(
			VIEW, name, {"times_opened": int(times) + 1, "last_seen_on": now}, update_modified=False
		)
		return {"tour": tour, "times_opened": int(times) + 1}
	doc = frappe.get_doc(
		{
			"doctype": VIEW,
			"user": user,
			"tour": tour,
			"times_opened": 1,
			"first_seen_on": now,
			"last_seen_on": now,
		}
	)
	# The app's own record of what it showed this person; nobody edits it.
	doc.insert(ignore_permissions=True)
	return {"tour": tour, "times_opened": 1}
