# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.api import filing_penalty
from kxcompliance.kx_compliance.doctype.compliance_client.test_compliance_client import task
from kxcompliance.kx_compliance.doctype.legal_case.test_legal_case import make_case
from kxcompliance.kx_compliance.obligation_library import sync_standard_templates
from kxcompliance.kx_compliance.score import company_scores, fee_figures, late_fee, rules_for
from kxcompliance.kx_compliance.test_utils import (
	TEST_COMPANY,
	make_company,
	make_item,
	make_item_type,
	make_users,
)

TEMPLATE = "Compliance Obligation Template"


def rules(**figures):
	values = {
		"late_fee_per_day": 0,
		"late_fee_flat": 0,
		"late_fee_cap": 0,
		"cap_at_tax": 0,
		"interest_percent": 0,
	}
	return frappe._dict({**values, **figures})


class TestComplianceScore(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		make_item_type("Test Score Licence", grace=0)

	def setUp(self):
		frappe.db.delete("Compliance Task", {"company": TEST_COMPANY})
		frappe.db.delete("Compliance Item", {"company": TEST_COMPANY})
		frappe.db.delete("Legal Case", {"company": TEST_COMPANY})

	def test_late_fees_follow_the_rule(self):
		gst = rules(late_fee_per_day=50, late_fee_cap=10000)
		self.assertEqual(late_fee(gst, 0), 0)
		self.assertEqual(late_fee(gst, 12), 600)
		self.assertEqual(late_fee(gst, 400), 10000)
		self.assertEqual(late_fee(rules(late_fee_flat=5000), 1), 5000)
		tds = rules(late_fee_per_day=200, cap_at_tax=1)
		self.assertEqual(late_fee(tds, 30, tax=4500), 4500)
		self.assertEqual(late_fee(tds, 30), 6000)  # tax not known yet: no cap to apply

	def test_a_filing_shows_what_lateness_costs(self):
		late = task(TEST_COMPANY)  # GSTR-3B (Monthly), due 20 Nov 2026
		with self.freeze_time("2026-12-02"):
			penalty = filing_penalty(late)
		self.assertEqual((penalty["days_late"], penalty["late_fee"]), (12, 600))
		self.assertEqual(penalty["late_fee_in_a_week"], 950)
		self.assertEqual(penalty["interest_percent"], 18)
		self.assertTrue(penalty["counted"])
		self.assertIn("s.47", penalty["rule"])
		self.assertIsNone(penalty["checked_on"])
		with self.freeze_time("2026-11-15"):
			early = filing_penalty(late)
		self.assertEqual((early["days_left"], early["late_fee"], early["late_fee_in_a_week"]), (5, 0, 100))

	def test_the_score_takes_points_off_for_what_needs_fixing(self):
		overdue = task(TEST_COMPANY)
		frappe.db.set_value("Compliance Task", overdue, "is_overdue", 1)
		late = task(TEST_COMPANY)
		frappe.db.set_value(
			"Compliance Task", late, {"status": "Filed Late", "effective_due_date": "2026-10-20"}
		)
		make_item("Test Score Licence", days=-5)  # expired
		make_item("Test Score Licence", days=10)  # due for renewal
		make_case(company=TEST_COMPANY)
		make_case(company=TEST_COMPANY, amount_involved=100000, risk="Probable")
		with self.freeze_time("2026-12-02"):
			result = company_scores([TEST_COMPANY])[TEST_COMPANY]
		# 100 - 10 overdue - 10 expired - 2 filed late - 3 due - 5 case - 10 probable
		self.assertEqual(result["score"], 60)
		self.assertEqual(
			[reason["key"] for reason in result["reasons"]],
			["overdue", "expired", "probable_case", "open_case", "due_for_renewal", "filed_late"],
		)
		self.assertEqual(result["late_fees_so_far"], 600)

	def test_a_late_nil_return_costs_the_nil_fee_and_fewer_points(self):
		late = task(TEST_COMPANY)  # GSTR-3B (Monthly), due 20 Nov 2026
		frappe.db.set_value("Compliance Task", late, {"is_nil": 1, "is_overdue": 1})
		with self.freeze_time("2026-12-02"):
			penalty = filing_penalty(late)
			result = company_scores([TEST_COMPANY])[TEST_COMPANY]
		# ₹20 a day for 12 days, and no interest on a nil tax.
		self.assertEqual((penalty["late_fee"], penalty["late_fee_in_a_week"]), (240, 380))
		self.assertEqual(penalty["interest_percent"], 0)
		self.assertTrue(penalty["nil"])
		self.assertEqual(result["score"], 97)
		self.assertEqual([reason["key"] for reason in result["reasons"]], ["overdue_nil"])
		self.assertEqual(result["late_fees_so_far"], 240)
		with self.freeze_time("2027-06-01"):
			self.assertEqual(filing_penalty(late)["late_fee"], 500)  # the cap for a NIL return

	def test_maharashtra_professional_tax_charges_its_fee_nil_or_not(self):
		pt = rules_for(["Professional Tax - Maharashtra"])["Professional Tax - Maharashtra"]
		self.assertEqual(late_fee(fee_figures(pt), 40), 1000)
		self.assertEqual(late_fee(fee_figures(pt, is_nil=True), 40), 1000)
		self.assertEqual(late_fee(fee_figures(pt, is_nil=True), 0), 0)
		# Elsewhere a state's figures are left to the firm, so a NIL return costs nothing here.
		karnataka = rules_for(["Professional Tax - Karnataka"])["Professional Tax - Karnataka"]
		self.assertEqual(late_fee(fee_figures(karnataka, is_nil=True), 40), 0)

	def test_a_clean_company_scores_full_and_never_below_zero(self):
		self.assertEqual(company_scores([TEST_COMPANY])[TEST_COMPANY]["score"], 100)
		for _number in range(12):
			frappe.db.set_value("Compliance Task", task(TEST_COMPANY), "is_overdue", 1)
		self.assertEqual(company_scores([TEST_COMPANY])[TEST_COMPANY]["score"], 0)

	def test_a_firms_own_figures_outlast_library_updates(self):
		frappe.get_doc(
			{
				"doctype": "Compliance Penalty Figures",
				"obligation_template": "DIR-3 KYC",
				"late_fee_flat": 7500,
			}
		).insert()
		frappe.db.set_value(TEMPLATE, "AOC-4 (Financial Statements)", "late_fee_per_day", 1)
		sync_standard_templates()
		self.assertEqual(rules_for(["DIR-3 KYC"])["DIR-3 KYC"].late_fee_flat, 7500)
		self.assertTrue(rules_for(["DIR-3 KYC"])["DIR-3 KYC"].penalty_set_by_firm)
		self.assertEqual(
			frappe.db.get_value(TEMPLATE, "AOC-4 (Financial Statements)", "late_fee_per_day"), 100
		)
