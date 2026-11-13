# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Periods and due dates of the shipped library, checked against the dates in the design."""

from datetime import date

import frappe
from frappe.tests import IntegrationTestCase

from compliance_plus.compliance_plus.statutory import due_date, period_label, periods


def due(template: str, period_end: str) -> date:
	return due_date(
		frappe.get_doc("Compliance Obligation Template", template), date.fromisoformat(period_end)
	)


class TestStatutoryRules(IntegrationTestCase):
	def test_monthly_periods(self):
		self.assertEqual(
			periods("Monthly", "Financial Year", date(2026, 10, 15), date(2026, 12, 31)),
			[
				(date(2026, 10, 1), date(2026, 10, 31)),
				(date(2026, 11, 1), date(2026, 11, 30)),
				(date(2026, 12, 1), date(2026, 12, 31)),
			],
		)

	def test_quarters_and_halves_follow_their_year(self):
		self.assertEqual(
			periods("Quarterly", "Financial Year", date(2026, 2, 1), date(2026, 6, 30)),
			[(date(2026, 1, 1), date(2026, 3, 31)), (date(2026, 4, 1), date(2026, 6, 30))],
		)
		self.assertEqual(
			periods("Half-yearly", "Financial Year", date(2026, 5, 1), date(2027, 3, 31)),
			[(date(2026, 4, 1), date(2026, 9, 30)), (date(2026, 10, 1), date(2027, 3, 31))],
		)
		self.assertEqual(
			periods("Half-yearly", "Calendar Year", date(2026, 5, 1), date(2026, 12, 31)),
			[(date(2026, 1, 1), date(2026, 6, 30)), (date(2026, 7, 1), date(2026, 12, 31))],
		)
		self.assertEqual(
			periods("Yearly", "Financial Year", date(2026, 1, 1), date(2027, 3, 31)),
			[(date(2025, 4, 1), date(2026, 3, 31)), (date(2026, 4, 1), date(2027, 3, 31))],
		)

	def test_gst_due_dates(self):
		self.assertEqual(due("GSTR-1 (Monthly)", "2026-10-31"), date(2026, 11, 11))
		self.assertEqual(due("GSTR-3B (Monthly)", "2026-10-31"), date(2026, 11, 20))
		self.assertEqual(due("GSTR-3B (QRMP, 22nd)", "2026-12-31"), date(2027, 1, 22))
		self.assertEqual(due("GSTR-9 (Annual Return)", "2027-03-31"), date(2027, 12, 31))

	def test_tds_due_dates_including_march(self):
		self.assertEqual(due("TDS/TCS Payment", "2027-02-28"), date(2027, 3, 7))
		self.assertEqual(due("TDS/TCS Payment", "2027-03-31"), date(2027, 4, 30))
		self.assertEqual(due("TDS Return 26Q (Non-salary)", "2026-06-30"), date(2026, 7, 31))
		self.assertEqual(due("TDS Return 26Q (Non-salary)", "2026-12-31"), date(2027, 1, 31))
		self.assertEqual(due("TDS Return 26Q (Non-salary)", "2027-03-31"), date(2027, 5, 31))
		self.assertEqual(due("Form 16A", "2026-06-30"), date(2026, 8, 15))
		self.assertEqual(due("Form 16A", "2027-03-31"), date(2027, 6, 15))
		self.assertEqual(due("Form 16", "2027-03-31"), date(2027, 6, 15))

	def test_income_tax_and_company_law_dates(self):
		self.assertEqual(due("Advance Tax", "2026-06-30"), date(2026, 6, 15))
		self.assertEqual(due("Advance Tax", "2027-03-31"), date(2027, 3, 15))
		self.assertEqual(due("Tax Audit Report", "2027-03-31"), date(2027, 9, 30))
		self.assertEqual(due("Income Tax Return (Audit Cases)", "2027-03-31"), date(2027, 10, 31))
		self.assertEqual(due("DIR-3 KYC", "2027-03-31"), date(2027, 9, 30))
		self.assertEqual(due("DPT-3 (Return of Deposits)", "2027-03-31"), date(2027, 6, 30))
		self.assertEqual(due("MSME-1 (Dues to MSMEs)", "2026-09-30"), date(2026, 10, 31))
		self.assertEqual(due("MSME-1 (Dues to MSMEs)", "2027-03-31"), date(2027, 4, 30))
		self.assertEqual(due("LLP Form 11 (Annual Return)", "2027-03-31"), date(2027, 5, 30))
		self.assertEqual(due("LLP Form 8 (Statement of Account)", "2027-03-31"), date(2027, 10, 30))

	def test_state_taxes_and_the_last_day_of_a_month(self):
		self.assertEqual(due("Professional Tax - Maharashtra", "2027-02-28"), date(2027, 2, 28))
		self.assertEqual(due("Professional Tax - Karnataka", "2026-10-31"), date(2026, 11, 20))
		self.assertEqual(due("Labour Welfare Fund - Maharashtra", "2026-06-30"), date(2026, 7, 15))
		self.assertEqual(due("Labour Welfare Fund - Karnataka", "2026-12-31"), date(2027, 1, 15))

	def test_period_labels(self):
		self.assertEqual(period_label("Monthly", "Financial Year", date(2026, 10, 1)), "Oct 2026")
		self.assertEqual(period_label("Quarterly", "Financial Year", date(2026, 7, 1)), "Q2 2026-27")
		self.assertEqual(period_label("Quarterly", "Financial Year", date(2027, 1, 1)), "Q4 2026-27")
		self.assertEqual(period_label("Half-yearly", "Calendar Year", date(2026, 7, 1)), "H2 2026")
		self.assertEqual(period_label("Yearly", "Financial Year", date(2026, 4, 1)), "FY 2026-27")

	def test_the_library_is_marked_standard_and_unchecked(self):
		templates = frappe.get_all(
			"Compliance Obligation Template", filters={"is_standard": 1}, fields=["checked_on"]
		)
		self.assertEqual(len(templates), 38)
		self.assertTrue(all(row.checked_on is None for row in templates))

	def test_a_template_due_after_the_agm_needs_its_days(self):
		template = frappe.get_doc(
			{
				"doctype": "Compliance Obligation Template",
				"template_name": "Test AGM filing",
				"law": "Companies Act",
				"frequency": "Yearly",
				"due_after_event": 1,
			}
		)
		with self.assertRaisesRegex(frappe.ValidationError, "days after the AGM"):
			template.insert()
