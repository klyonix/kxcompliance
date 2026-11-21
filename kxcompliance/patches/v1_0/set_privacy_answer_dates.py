# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Privacy requests made before the 30-day target: each gets its latest date by law, 90 days after
it came in, and one still open is to be answered within 30 days of it. Only requests without the
latest date are touched, so running it again changes nothing."""

import frappe
from frappe.query_builder import Interval
from frappe.query_builder.functions import Date

from kxcompliance import scoped
from kxcompliance.kx_compliance.privacy import RESPONSE_DAYS, TARGET_DAYS


def execute():
	request = frappe.qb.DocType("Privacy Request")
	untouched = request.latest_by.isnull() & request.received_on.isnotnull() & scoped.where(request)
	(
		frappe.qb.update(request)
		.set(request.due_by, Date(request.received_on) + Interval(days=TARGET_DAYS))
		.where(untouched & request.status.isin(["Open", "In Progress"]))
	).run()
	(
		frappe.qb.update(request)
		.set(request.latest_by, Date(request.received_on) + Interval(days=RESPONSE_DAYS))
		.where(untouched)
	).run()
