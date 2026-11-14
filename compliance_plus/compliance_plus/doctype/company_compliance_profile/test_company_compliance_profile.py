# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from compliance_plus.api import boot, complete_onboarding, onboarding_options
from compliance_plus.compliance_plus.test_utils import HOLDER, MANAGER, REVIEWER, make_company, make_users

# These tests build their own records; skip ERPNext's generated ones.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Company", "User"]

SETTINGS = "Compliance Plus Settings"
NEW_COMPANY = "Onboarding Test Traders Private Limited"


def answers(**overrides) -> dict:
	values = {
		"account_type": "Organisation",
		"new_company": NEW_COMPANY,
		"company_type": "Private Limited",
		"registrations": [
			{"registration_type": "GST", "registration_number": "29AAACO1234F1Z5", "state": "Karnataka"},
			{"registration_type": "TAN", "registration_number": "BLRO12345F"},
		],
		"responsible": HOLDER,
		"reviewer": REVIEWER,
	}
	values.update(overrides)
	return values


class TestOnboarding(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()

	def setUp(self):
		# Each test starts from a site that has not been set up, without the company it makes.
		frappe.db.set_single_value(SETTINGS, {"setup_complete": 0, "account_type": ""})
		if frappe.db.exists("Company Compliance Profile", NEW_COMPANY):
			frappe.delete_doc("Company Compliance Profile", NEW_COMPANY, force=True)
		frappe.db.delete("Compliance Task", {"company": NEW_COMPANY})

	def test_managers_are_sent_to_onboarding_until_it_is_done(self):
		with self.set_user(MANAGER):
			self.assertTrue(boot()["setup_needed"])
			options = onboarding_options()
		self.assertIn("LLP", options["company_types"])
		self.assertIn("GST Composition", options["registration_types"])
		self.assertIn(HOLDER, [person.name for person in options["people"]])
		with self.set_user(HOLDER):
			self.assertFalse(boot()["setup_needed"])
			with self.assertRaises(frappe.PermissionError):
				onboarding_options()
			with self.assertRaises(frappe.PermissionError):
				complete_onboarding(answers())

	def test_a_compliance_manager_without_company_rights_chooses_an_existing_company(self):
		with self.set_user(MANAGER):
			self.assertFalse(onboarding_options()["can_create_company"])
			with self.assertRaisesRegex(frappe.PermissionError, "cannot create companies"):
				complete_onboarding(answers(new_company="Another New Company Private Limited"))

	def test_an_organisation_gets_its_company_calendar_and_first_filings(self):
		# A System Manager may create the company as part of onboarding.
		with (
			self.change_settings(SETTINGS, generation_horizon_days=45),
			self.set_user("Administrator"),
			self.freeze_time("2026-11-15"),
		):
			if frappe.db.exists("Company", NEW_COMPANY):
				result = complete_onboarding(answers(new_company=None, company=NEW_COMPANY))
			else:
				result = complete_onboarding(answers())
		self.assertEqual(result["company"], NEW_COMPANY)
		self.assertGreater(result["obligations"], 5)
		self.assertGreater(result["tasks"], 0)
		profile = frappe.get_doc("Company Compliance Profile", NEW_COMPANY)
		self.assertEqual((profile.default_responsible, profile.default_reviewer), (HOLDER, REVIEWER))
		templates = {row.obligation_template for row in profile.obligations}
		self.assertTrue({"GSTR-3B (Monthly)", "TDS/TCS Payment", "AOC-4 (Financial Statements)"} <= templates)
		self.assertEqual(frappe.db.get_single_value(SETTINGS, "account_type"), "Organisation")
		with self.set_user("Administrator"):
			self.assertFalse(boot()["setup_needed"])
			with self.assertRaisesRegex(frappe.ValidationError, "already set up"):
				complete_onboarding(answers(new_company=None, company=NEW_COMPANY))

	def test_a_firm_names_the_app_after_itself(self):
		frappe.db.set_single_value(SETTINGS, "app_name", "Compliance Plus")
		with self.set_user(MANAGER), self.freeze_time("2026-11-15"):
			complete_onboarding(
				answers(
					account_type="CA/CS Firm",
					firm_name="Rao & Associates",
					new_company=None,
					company="Compliance Test Company",
				)
			)
		self.assertEqual(frappe.db.get_single_value(SETTINGS, "account_type"), "CA/CS Firm")
		self.assertEqual(frappe.db.get_single_value(SETTINGS, "app_name"), "Rao & Associates")
		frappe.delete_doc("Company Compliance Profile", "Compliance Test Company", force=True)

	def test_answers_are_checked_before_anything_is_made(self):
		with self.set_user(MANAGER):
			with self.assertRaisesRegex(frappe.ValidationError, "choose the state"):
				complete_onboarding(
					answers(
						registrations=[{"registration_type": "GST", "registration_number": "29AAACO1234F1Z5"}]
					)
				)
			with self.assertRaisesRegex(frappe.ValidationError, "not a registration"):
				complete_onboarding(
					answers(registrations=[{"registration_type": "VAT", "registration_number": "X1"}])
				)
			with self.assertRaisesRegex(frappe.ValidationError, "organisation or a CA/CS firm"):
				complete_onboarding(answers(account_type="Club"))
		self.assertFalse(frappe.db.get_single_value(SETTINGS, "setup_complete"))
