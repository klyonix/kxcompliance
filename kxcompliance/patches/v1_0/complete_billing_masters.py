# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""A firm set up to bill before government fees were kept free of GST gets the item tax template
that does so. Safe to run again: billing's masters are each made only if they are not there."""

import frappe

from kxcompliance.kx_compliance.billing import make_masters


def execute():
	company = frappe.db.get_single_value("KX Compliance Settings", "billing_company")
	if company and frappe.db.exists("Company", company):
		make_masters(company)
