# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.api import boot, complete_onboarding, onboarding_options
from kxcompliance.kx_compliance.test_utils import (
	HOLDER,
	MANAGER,
	REVIEWER,
	TEST_COMPANY,
	make_company,
	make_users,
)

# These tests build their own records; skip ERPNext's generated ones.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Company", "User"]

SETTINGS = "KX Compliance Settings"
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

	def test_last_years_agm_makes_its_filings_at_setup(self):
		# Set up in November: the AGM for the year ended March 2026 was on 30 September, so MGT-7
		# (60 days after) is due on 29 November and made; AOC-4 fell due in October, before setup.
		with (
			self.change_settings(SETTINGS, generation_horizon_days=45),
			self.set_user("Administrator"),
			self.freeze_time("2026-11-15"),
		):
			options = onboarding_options()
			self.assertIn("Private Limited", options["agm_company_types"])
			self.assertNotIn("LLP", options["agm_company_types"])
			self.assertEqual(str(options["last_year_end"]), "2026-03-31")
			company = (
				{"new_company": None, "company": NEW_COMPANY}
				if frappe.db.exists("Company", NEW_COMPANY)
				else {}
			)
			complete_onboarding(answers(agm_date="2026-09-30", **company))
		agm = frappe.get_doc("Company Compliance Profile", NEW_COMPANY).agm_dates
		self.assertEqual(
			[(str(row.financial_year_end), str(row.agm_date)) for row in agm], [("2026-03-31", "2026-09-30")]
		)
		due = {
			row.obligation_template: str(row.due_date)
			for row in frappe.get_all(
				"Compliance Task",
				filters={"company": NEW_COMPANY},
				fields=["obligation_template", "due_date"],
			)
		}
		self.assertNotIn("AOC-4 (Financial Statements)", due)
		self.assertEqual(due.get("MGT-7 / MGT-7A (Annual Return)"), "2026-11-29")

	def test_whoever_sets_the_app_up_is_the_grievance_officer_until_one_is_named(self):
		frappe.db.set_single_value(SETTINGS, {"grievance_officer": None, "grievance_email": None})
		with self.set_user(MANAGER), self.freeze_time("2026-11-15"):
			complete_onboarding(answers(new_company=None, company=TEST_COMPANY))
		self.assertEqual(frappe.db.get_single_value(SETTINGS, "grievance_email"), MANAGER)
		self.assertTrue(frappe.db.get_single_value(SETTINGS, "grievance_officer"))
		frappe.delete_doc("Company Compliance Profile", TEST_COMPANY, force=True)

	def test_an_agm_date_outside_the_year_is_refused(self):
		with self.set_user("Administrator"), self.freeze_time("2026-11-15"):
			for held in ("2026-03-15", "2026-12-01"):
				with self.assertRaisesRegex(frappe.ValidationError, "year ended"):
					complete_onboarding(answers(agm_date=held))
		self.assertFalse(frappe.db.get_single_value(SETTINGS, "setup_complete"))

	def test_a_firm_names_the_app_after_itself(self):
		frappe.db.set_single_value(SETTINGS, "app_name", "KlyONIX Compliance")
		with self.set_user(MANAGER), self.freeze_time("2026-11-15"):
			complete_onboarding(
				answers(
					account_type="CA/CS Firm",
					firm_name="Rao & Associates",
					client_name="Onboarding Test Group",
					new_company=None,
					company="Compliance Test Company",
				)
			)
		self.assertEqual(frappe.db.get_single_value(SETTINGS, "account_type"), "CA/CS Firm")
		self.assertEqual(frappe.db.get_single_value(SETTINGS, "app_name"), "Rao & Associates")
		self.assertEqual(
			frappe.db.get_value("Company Compliance Profile", "Compliance Test Company", "client"),
			"Onboarding Test Group",
		)
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


APP_COMPANY = "App Test Traders Private Limited"


class TestCompaniesInTheApp(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		# A Compliance Manager sets up an existing company; creating one needs a System Manager.
		if not frappe.db.exists("Company", APP_COMPANY):
			frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": APP_COMPANY,
					"abbr": "ATTPL",
					"default_currency": "INR",
					"country": "India",
				}
			).insert()

	def setUp(self):
		for company in (NEW_COMPANY, APP_COMPANY):
			if frappe.db.exists("Company Compliance Profile", company):
				frappe.delete_doc("Company Compliance Profile", company, force=True)
			frappe.db.delete("Compliance Task", {"company": company})

	def test_a_manager_sets_a_company_up_and_changes_it(self):
		from kxcompliance.api import companies_overview, company_detail, save_company

		values = {
			"company_type": "Private Limited",
			"default_responsible": HOLDER,
			"default_reviewer": REVIEWER,
			"registrations": [
				{"registration_type": "GST", "registration_number": "29AAACA1234F1Z5", "state": "Karnataka"}
			],
		}
		with self.set_user(MANAGER):
			made = save_company(APP_COMPANY, values)
			self.assertGreater(made["obligations"], 0)
			detail = company_detail(made["company"])
			before = len(detail["obligations"])
			first = detail["obligations"][0]
			values["registrations"].append({"registration_type": "TAN", "registration_number": "BLRA12345A"})
			values["obligations"] = [{"name": first["name"], "is_active": 0, "responsible": REVIEWER}]
			changed = save_company(made["company"], values)
			detail = company_detail(made["company"])
			overview = companies_overview()
		self.assertGreater(changed["obligations"], 0)
		self.assertGreater(len(detail["obligations"]), before)
		row = next(row for row in detail["obligations"] if row["name"] == first["name"])
		self.assertEqual((row["is_active"], row["responsible"]), (0, REVIEWER))
		self.assertIn(made["company"], [row.company for row in overview["companies"]])
		self.assertNotIn(made["company"], overview["not_set_up"])

	def test_each_obligation_has_its_own_reviewer_never_its_preparer(self):
		from kxcompliance.api import company_detail, save_company

		values = {
			"company_type": "Private Limited",
			"default_responsible": HOLDER,
			"default_reviewer": REVIEWER,
		}
		with self.set_user(MANAGER):
			save_company(APP_COMPANY, values)
			first = company_detail(APP_COMPANY)["obligations"][0]
			values["obligations"] = [
				{"name": first["name"], "is_active": 1, "responsible": "", "reviewer": MANAGER}
			]
			save_company(APP_COMPANY, values)
			row = next(
				row for row in company_detail(APP_COMPANY)["obligations"] if row["name"] == first["name"]
			)
			# Left to the company's default, the row takes that person, so its filings have one.
			self.assertEqual((row["responsible"], row["reviewer"]), (HOLDER, MANAGER))
			values["obligations"] = [
				{"name": first["name"], "is_active": 1, "responsible": MANAGER, "reviewer": MANAGER}
			]
			with self.assertRaisesRegex(frappe.ValidationError, "cannot also review it"):
				save_company(APP_COMPANY, values)
			with self.assertRaisesRegex(frappe.ValidationError, "default reviewer"):
				save_company(APP_COMPANY, {**values, "obligations": [], "default_reviewer": HOLDER})

	def test_a_companys_agm_dates_are_kept_and_checked(self):
		from kxcompliance.api import company_detail, save_company

		values = {"company_type": "Private Limited", "default_responsible": HOLDER}
		with self.set_user(MANAGER):
			save_company(APP_COMPANY, values)
			values["agm_dates"] = [{"financial_year_end": "2026-03-31", "agm_date": "2026-09-25"}]
			save_company(APP_COMPANY, values)
			detail = company_detail(APP_COMPANY)
			self.assertEqual(
				detail["agm_dates"], [{"financial_year_end": "2026-03-31", "agm_date": "2026-09-25"}]
			)
			self.assertIn("AOC-4 (Financial Statements)", detail["agm_filings"])
			values["agm_dates"] = [{"financial_year_end": "2026-03-31", "agm_date": "2026-03-01"}]
			with self.assertRaisesRegex(frappe.ValidationError, "not after the year ending"):
				save_company(APP_COMPANY, values)
			values["agm_dates"] = [
				{"financial_year_end": "2026-03-31", "agm_date": "2026-09-25"},
				{"financial_year_end": "2026-03-31", "agm_date": "2026-09-28"},
			]
			with self.assertRaisesRegex(frappe.ValidationError, "two AGMs"):
				save_company(APP_COMPANY, values)
			del values["agm_dates"]
			save_company(APP_COMPANY, values)
			self.assertEqual(len(company_detail(APP_COMPANY)["agm_dates"]), 1)

	def test_only_known_people_and_managers(self):
		from kxcompliance.api import save_company

		values = {"company_type": "Private Limited", "default_responsible": "nobody@example.com"}
		with self.set_user(MANAGER), self.assertRaises(frappe.ValidationError):
			save_company(TEST_COMPANY, values)
		values["default_responsible"] = HOLDER
		with self.set_user(HOLDER), self.assertRaises(frappe.PermissionError):
			save_company(TEST_COMPANY, values)

	def test_a_new_company_needs_rights_to_create_companies(self):
		from kxcompliance.api import save_company

		values = {"company_type": "Private Limited", "default_responsible": HOLDER}
		with self.set_user(MANAGER), self.assertRaises(frappe.PermissionError):
			save_company("Brand New Foods Private Limited", values, new_company=True)


class TestNobodyReviewsTheirOwn(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()

	def test_companies_set_up_before_the_rule_can_be_saved_again(self):
		from kxcompliance.kx_compliance.doctype.compliance_client.test_compliance_client import profile
		from kxcompliance.patches.v1_0.clear_self_review import execute as clear_self_review

		name = profile(TEST_COMPANY).name  # MANAGER prepares its filings by default
		# As data made before the rule could be: the default reviewer, and an obligation whose
		# reviewer is the person who prepares it.
		frappe.db.set_value("Company Compliance Profile", name, "default_reviewer", MANAGER)
		row = frappe.get_doc(
			{
				"doctype": "Company Obligation",
				"parent": name,
				"parenttype": "Company Compliance Profile",
				"parentfield": "obligations",
				"obligation_template": "GSTR-3B (Monthly)",
				"responsible": MANAGER,
				"reviewer": MANAGER,
				"start_from": "2026-04-01",
				"idx": 99,
			}
		)
		row.db_insert()
		with self.assertRaisesRegex(frappe.ValidationError, "cannot be both"):
			frappe.get_doc("Company Compliance Profile", name).save()
		clear_self_review()
		clear_self_review()  # safe to run again
		self.assertIsNone(frappe.db.get_value("Company Compliance Profile", name, "default_reviewer"))
		self.assertIsNone(frappe.db.get_value("Company Obligation", row.name, "reviewer"))
		frappe.get_doc("Company Compliance Profile", name).save()
