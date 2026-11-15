# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Bills made before bills named a company (Nov 2026): a bill of a client with one company was for
that company, so it is marked so. Bills of clients with several companies stay billed to the
client as a whole, since which company each was for is not known. Safe to run again: only bills
not yet marked are read."""

import frappe
from frappe.query_builder.functions import Count, Max


def execute():
	if not frappe.db.has_column("Sales Invoice", "billed_company"):
		# Fixtures sync after patches; the field this fills must exist first.
		from frappe.utils.fixtures import sync_fixtures

		sync_fixtures("kxcompliance")
	profile = frappe.qb.DocType("Company Compliance Profile")
	single = (
		frappe.qb.from_(profile)
		.select(profile.client, Max(profile.company).as_("company"))
		.where(profile.client.isnotnull())
		.groupby(profile.client)
		.having(Count(profile.name) == 1)
	).run(as_dict=True)
	invoice = frappe.qb.DocType("Sales Invoice")
	for row in single:
		(
			frappe.qb.update(invoice)
			.set(invoice.billed_company, row.company)
			.where((invoice.compliance_client == row.client) & invoice.billed_company.isnull())
		).run()
