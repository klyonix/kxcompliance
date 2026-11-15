# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.api import app_companies, billing_setup, set_up_billing
from kxcompliance.kx_compliance.billing import OUTSIDE_STATE, WITHIN_STATE, state_of
from kxcompliance.kx_compliance.companies import companies_overview
from kxcompliance.kx_compliance.register import compliance_companies
from kxcompliance.kx_compliance.test_utils import HOLDER, make_company, make_users

SETTINGS = "KX Compliance Settings"
FIRM = "Billing Test Associates"
DETAILS = {
	"billing_gstin": "29aaaca1234f1z5",
	"billing_address": "12 MG Road, Bengaluru",
	"bank_details": "Test Bank, A/c 0001, IFSC TEST0000001",
	"bill_prefix": "BTA",
}


def rates(company: str, title: str) -> list[tuple[str, float]]:
	template = frappe.db.get_value("Sales Taxes and Charges Template", {"company": company, "title": title})
	return sorted(
		(frappe.db.get_value("Account", row.account_head, "account_name"), row.rate)
		for row in frappe.get_doc("Sales Taxes and Charges Template", template).taxes
	)


class TestBillingSetup(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()

	def test_a_firm_sets_up_its_own_company_to_bill_from_once(self):
		with self.change_settings(SETTINGS, account_type="CA/CS Firm", billing_company=None):
			state = set_up_billing(DETAILS, name=FIRM)
			company = state["company"]
			# The GSTIN is kept as written in capitals, and says the firm is in Karnataka.
			self.assertEqual(
				(state["billing_gstin"], state["billing_state"]), ("29AAACA1234F1Z5", "Karnataka")
			)
			self.assertEqual(frappe.db.get_value("Company", company, "tax_id"), "29AAACA1234F1Z5")
			self.assertTrue(frappe.db.exists("Item", "Professional fees"))
			self.assertTrue(frappe.db.exists("Item", "Government fees (reimbursed)"))
			self.assertEqual(rates(company, WITHIN_STATE), [("Output CGST", 9), ("Output SGST", 9)])
			self.assertEqual(rates(company, OUTSIDE_STATE), [("Output IGST", 18)])
			# Setting up again keeps the company and makes nothing twice.
			again = set_up_billing({**DETAILS, "bill_prefix": "BTA2"})
			self.assertEqual(again["company"], company)
			self.assertEqual(frappe.db.count("Sales Taxes and Charges Template", {"company": company}), 2)
			self.assertEqual(billing_setup()["bill_prefix"], "BTA2")
			# The firm's company is not a client's: it stays out of everything compliance.
			self.assertNotIn(company, compliance_companies())
			self.assertNotIn(company, app_companies())
			self.assertNotIn(company, companies_overview()["not_set_up"])

	def test_billing_is_for_a_firms_managers_and_takes_only_its_details(self):
		with self.change_settings(SETTINGS, account_type="Organisation"):
			with self.assertRaisesRegex(frappe.PermissionError, "CA/CS firms"):
				billing_setup()
		with self.change_settings(SETTINGS, account_type="CA/CS Firm"):
			with self.set_user(HOLDER), self.assertRaisesRegex(frappe.PermissionError, "Compliance Manager"):
				billing_setup()
			with self.assertRaisesRegex(frappe.ValidationError, "firm's name"):
				with self.change_settings(SETTINGS, billing_company=None):
					set_up_billing(DETAILS)

	def test_a_gstin_says_its_state_and_a_wrong_one_is_refused(self):
		self.assertEqual(state_of("27AAACA1234F1Z5"), "Maharashtra")
		self.assertEqual(state_of("", "Goa"), "Goa")
		with self.assertRaisesRegex(frappe.ValidationError, "GSTIN pattern"):
			state_of("29ABC")
