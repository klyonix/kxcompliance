# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Nobody reviews their own filing (Nov 2026), and an obligation left to the company's default
person now takes that person when saved. Companies set up before either can break the rule
without anyone choosing to, so they could no longer be saved: their default reviewer, or an
obligation's reviewer, is the person who prepares it. That reviewer is cleared; the filings then
go without review until one is chosen, as for any company with no reviewer. Safe to run again:
only rows that still break the rule are read."""

import frappe
from frappe.query_builder.functions import Coalesce, NullIf


def execute():
	profile = frappe.qb.DocType("Company Compliance Profile")
	(
		frappe.qb.update(profile)
		.set(profile.default_reviewer, None)
		.where(
			profile.default_reviewer.isnotnull() & (profile.default_reviewer == profile.default_responsible)
		)
	).run()
	row = frappe.qb.DocType("Company Obligation")
	(
		frappe.qb.update(row)
		.join(profile)
		.on(profile.name == row.parent)
		.set(row.reviewer, None)
		.where(
			(row.parenttype == "Company Compliance Profile")
			& row.reviewer.isnotnull()
			& (row.reviewer == Coalesce(NullIf(row.responsible, ""), profile.default_responsible))
		)
	).run()
