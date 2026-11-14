# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.kx_compliance.legal import run_daily
from kxcompliance.kx_compliance.move_old_trackers import move_hearings
from kxcompliance.kx_compliance.report.case_register.case_register import execute as case_register
from kxcompliance.kx_compliance.report.contingent_liabilities.contingent_liabilities import (
	execute as contingent_report,
)
from kxcompliance.kx_compliance.test_utils import (
	AUDITOR,
	HOLDER,
	MANAGER,
	OTHER_HOLDER,
	REVIEWER,
	TEST_COMPANY,
	make_company,
	make_users,
)

# These tests build their own records; skip ERPNext's generated ones.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Company", "User", "Supplier", "Branch", "Currency"]

SETTINGS = "KX Compliance Settings"


def make_case(**fields):
	values = {
		"doctype": "Legal Case",
		"title": "Test recovery suit",
		"forum": "District Court",
		"filing_date": "2026-01-10",
		"company": TEST_COMPANY,
		"our_role": "Petitioner",
		"responsible": HOLDER,
		"reviewer": REVIEWER,
	}
	values.update(fields)
	return frappe.get_doc(values).insert()


def make_date(case: str, date: str, **fields):
	return frappe.get_doc(
		{
			"doctype": "Legal Date",
			"reference_doctype": "Legal Case",
			"reference_name": case,
			"date": date,
			**fields,
		}
	).insert()


class TestLegalCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		frappe.defaults.set_global_default("company", TEST_COMPANY)

	def setUp(self):
		# Data stays until the class ends, so clear what an earlier test may have left.
		frappe.db.delete("Legal Date")
		frappe.db.delete("Compliance Reminder Log")

	def test_closing_a_case_records_when_and_reopening_clears_it(self):
		case = make_case()
		case.status = "Settled"
		case.save()
		self.assertTrue(case.closed_on)
		case.status = "Open"
		case.save()
		self.assertIsNone(case.closed_on)

	def test_an_amount_needs_a_risk(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Set the Risk"):
			make_case(amount_involved=500000)

	def test_a_case_cannot_appeal_itself(self):
		case = make_case()
		case.appeal_of = case.name
		with self.assertRaisesRegex(frappe.ValidationError, "appeal of itself"):
			case.save()

	def test_a_date_takes_its_title_and_people_from_the_case(self):
		case = make_case()
		hearing = make_date(case.name, "2027-01-15")
		self.assertEqual(hearing.reference_title, case.title)
		self.assertEqual((hearing.responsible, hearing.reviewer), (HOLDER, REVIEWER))
		case.responsible = OTHER_HOLDER
		case.save()
		self.assertEqual(frappe.db.get_value("Legal Date", hearing.name, "responsible"), OTHER_HOLDER)

	def test_a_date_belongs_to_a_case_or_a_trademark_only(self):
		with self.assertRaisesRegex(frappe.ValidationError, "belongs to one of"):
			frappe.get_doc(
				{
					"doctype": "Legal Date",
					"reference_doctype": "User",
					"reference_name": HOLDER,
					"date": "2027-01-01",
				}
			).insert()

	def test_recording_an_outcome_with_a_next_date_makes_the_next_hearing_once(self):
		case = make_case()
		hearing = make_date(case.name, "2026-11-01")
		self.assertEqual(str(frappe.db.get_value("Legal Case", case.name, "next_date")), "2026-11-01")
		hearing.update(
			{"status": "Adjourned", "proceedings": "Respondent sought time", "next_date": "2026-12-05"}
		)
		hearing.save()
		hearing.save()
		following = frappe.get_all(
			"Legal Date", filters={"reference_name": case.name, "status": "Scheduled"}, pluck="date"
		)
		self.assertEqual([str(day) for day in following], ["2026-12-05"])
		self.assertEqual(str(frappe.db.get_value("Legal Case", case.name, "next_date")), "2026-12-05")

	def test_a_hearing_outcome_needs_what_happened_and_a_later_next_date(self):
		hearing = make_date(make_case().name, "2026-11-01")
		hearing.status = "Done"
		with self.assertRaisesRegex(frappe.ValidationError, "what happened"):
			hearing.save()
		hearing = frappe.get_doc("Legal Date", hearing.name)
		hearing.update({"status": "Done", "proceedings": "Heard", "next_date": "2026-10-01"})
		with self.assertRaisesRegex(frappe.ValidationError, "must be after"):
			hearing.save()

	def test_a_compliance_user_reaches_only_their_cases_and_dates(self):
		mine = make_case()
		theirs = make_case(responsible=OTHER_HOLDER, reviewer=MANAGER)
		their_date = make_date(theirs.name, "2027-02-01").name
		with self.set_user(HOLDER):
			self.assertEqual(
				set(frappe.get_list("Legal Case", pluck="name")) & {mine.name, theirs.name}, {mine.name}
			)
			self.assertFalse(frappe.has_permission("Legal Date", "read", their_date))
			make_date(mine.name, "2027-02-02")
			with self.assertRaises(frappe.PermissionError):
				make_date(theirs.name, "2027-02-03")

	def test_reminders_go_once_and_a_missing_outcome_is_escalated_once(self):
		hearing = make_date(make_case().name, "2026-11-20")

		def logs(kind):
			return frappe.get_all(
				"Compliance Reminder Log", filters={"kind": kind, "legal_date": hearing.name}
			)

		with self.change_settings(SETTINGS, enabled=1):
			for day in ("2026-11-18", "2026-11-18", "2026-11-22", "2026-11-23"):
				with self.freeze_time(day):
					run_daily()
		self.assertEqual(len(logs("Reminder")), 1)
		self.assertEqual(len(logs("Escalation")), 1)
		self.assertTrue(frappe.db.get_value("Legal Date", hearing.name, "is_overdue"))

	def test_contingent_liabilities_are_as_at_the_chosen_date(self):
		open_case = make_case(amount_involved=900000, provision=100000, risk="Probable")
		closed = make_case(amount_involved=200000, risk="Possible")
		closed.status = "Withdrawn"
		closed.save()
		frappe.db.set_value("Legal Case", closed.name, "closed_on", "2026-06-30")

		def names(as_at):
			_columns, rows = contingent_report({"as_at": as_at, "company": TEST_COMPANY})
			return {row.name: row for row in rows}

		before = names("2026-03-31")
		self.assertIn(closed.name, before)
		self.assertEqual(before[open_case.name].not_provided, 800000)
		self.assertNotIn(closed.name, names("2026-09-30"))

	def test_hearing_tracker_rows_move_to_cases(self):
		past = frappe.get_doc(
			{
				"doctype": "Hearing Tracker",
				"document_name": "Old labour matter",
				"issuer_supplier": "Labour Court, Pune",
				"issue_date": "2025-06-01",
				"expiry_date": "2025-09-01",
				"status": "Active",
				"agent_name": "A. Advocate",
			}
		).insert(ignore_permissions=True)
		first = move_hearings()
		again = move_hearings()
		self.assertEqual(again["moved"], 0)
		self.assertGreaterEqual(first["moved"], 1)
		case = frappe.get_doc("Legal Case", {"source_doctype": "Hearing Tracker", "source_name": past.name})
		self.assertEqual(case.forum_name, "Labour Court, Pune")
		self.assertIn("A. Advocate", case.summary)
		hearing = frappe.get_doc("Legal Date", {"reference_name": case.name})
		self.assertEqual(hearing.status, "Done")


class TestLegalCaseAmounts(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()

	def test_amounts_and_risk_are_for_managers_and_auditors_only(self):
		case = make_case(amount_involved=500000, provision=100000, risk="Possible")
		with self.set_user(HOLDER):
			read = frappe.get_doc("Legal Case", case.name)
			read.apply_fieldlevel_read_permissions()
			self.assertFalse(read.get("amount_involved"))
			self.assertFalse(read.get("risk"))
			columns, rows = case_register({})
			self.assertNotIn("amount_involved", [column["fieldname"] for column in columns])
			self.assertIn(case.name, [row.name for row in rows])
		with self.set_user(AUDITOR):
			columns, rows = case_register({})
			row = next(row for row in rows if row.name == case.name)
			self.assertEqual(row.amount_involved, 500000)

	def test_a_compliance_user_saving_a_case_keeps_its_amounts(self):
		case = make_case(amount_involved=500000, provision=100000, risk="Possible")
		with self.set_user(HOLDER):
			mine = frappe.get_doc("Legal Case", case.name)
			mine.amount_involved = 1
			mine.opposing_party = "Acme Traders"
			mine.save()
		self.assertEqual(frappe.db.get_value("Legal Case", case.name, "amount_involved"), 500000)
