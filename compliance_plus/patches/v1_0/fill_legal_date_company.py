# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Legal Dates now carry the company of their case or trademark; fill it in for existing dates.
Safe to run again: it only copies the company the case or trademark has now."""

import frappe

from compliance_plus.compliance_plus.legal import REFERENCE_COMPANIES, pass_company_to_dates


def execute():
	for doctype, company_field in REFERENCE_COMPANIES.items():
		dated = set(
			frappe.get_all("Legal Date", filters={"reference_doctype": doctype}, pluck="reference_name")
		)
		if not dated:
			continue
		for row in frappe.get_all(
			doctype, filters={"name": ("in", list(dated))}, fields=["name", f"{company_field} as company"]
		):
			pass_company_to_dates(doctype, row.name, row.company)
