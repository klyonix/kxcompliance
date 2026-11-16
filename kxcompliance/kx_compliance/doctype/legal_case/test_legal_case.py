# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.kx_compliance.legal import check_status_change, run_daily
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

	def test_closing_a_case_cancels_its_scheduled_dates(self):
		case = make_case()
		done = make_date(case.name, "2026-02-01", kind="Reply Due")
		done.status = "Done"
		done.save()
		hearing = make_date(case.name, "2027-03-01", kind="Hearing")
		with self.set_user(HOLDER):
			frappe.get_doc("Legal Case", case.name).change_status(
				"Disposed - In Our Favour", outcome="Suit decreed with costs", closed_on="2026-11-01"
			)
		case.reload()
		self.assertEqual((case.status, str(case.closed_on)), ("Disposed - In Our Favour", "2026-11-01"))
		self.assertIn("Suit decreed", case.outcome)
		self.assertEqual(frappe.db.get_value("Legal Date", hearing.name, "status"), "Cancelled")
		# What already happened stays as it was, and nothing is left to remind about.
		self.assertEqual(frappe.db.get_value("Legal Date", done.name, "status"), "Done")
		self.assertIsNone(case.next_date)

	def test_a_case_is_not_closed_in_the_future_or_moved_to_its_own_status(self):
		case = make_case()
		with self.assertRaisesRegex(frappe.ValidationError, "cannot be in the future"):
			case.change_status("Settled", closed_on="2999-01-01")
		with self.assertRaisesRegex(frappe.ValidationError, "already Open"):
			frappe.get_doc("Legal Case", case.name).change_status("Open")
		with self.assertRaisesRegex(frappe.ValidationError, "not a status"):
			frappe.get_doc("Legal Case", case.name).change_status("Won")

	def test_only_its_holder_reviewer_or_a_manager_changes_its_status(self):
		case = make_case()
		case.load_doc_before_save()
		case.status = "Stayed"
		for user in (HOLDER, REVIEWER, MANAGER):
			with self.set_user(user):
				check_status_change(case)
		with (
			self.set_user(OTHER_HOLDER),
			self.assertRaisesRegex(frappe.PermissionError, "from Open to Stayed"),
		):
			check_status_change(case)

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

	def test_a_missed_hearing_keeps_its_next_date(self):
		case = make_case()
		hearing = make_date(case.name, "2026-11-01", kind="Hearing")
		hearing.update({"status": "Missed", "next_date": "2026-12-10"})
		hearing.save()
		self.assertTrue(hearing.next_legal_date)
		self.assertEqual(str(frappe.db.get_value("Legal Case", case.name, "next_date")), "2026-12-10")

	def test_a_date_is_moved_only_while_it_is_ahead(self):
		case = make_case()
		hearing = make_date(case.name, "2027-01-10", kind="Hearing")
		hearing.date = "2027-01-17"
		hearing.save()
		self.assertEqual(str(frappe.db.get_value("Legal Case", case.name, "next_date")), "2027-01-17")
		hearing.update({"status": "Done", "proceedings": "Heard"})
		hearing.save()
		hearing.date = "2027-01-24"
		with self.assertRaisesRegex(frappe.ValidationError, "cannot be moved"):
			hearing.save()

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

	def test_a_manager_alone_changes_amounts_and_risk_in_the_app(self):
		from kxcompliance.api import editable_fields, save_changes

		case = make_case()
		with self.set_user(HOLDER):
			self.assertNotIn("risk", editable_fields("Legal Case")["fields"])
			with self.assertRaisesRegex(frappe.PermissionError, "cannot change amount_involved"):
				save_changes("Legal Case", case.name, {"amount_involved": 1, "risk": "Remote"})
		with self.set_user(MANAGER):
			self.assertIn("risk", editable_fields("Legal Case")["fields"])
			save_changes("Legal Case", case.name, {"risk": "Probable", "amount_involved": 250000})
		self.assertEqual(
			frappe.db.get_value("Legal Case", case.name, ["risk", "amount_involved"]), ("Probable", 250000)
		)


class TestStartingInTheApp(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()

	def test_a_case_under_way_starts_with_its_next_hearing_held_by_whoever_starts_it(self):
		from kxcompliance.api import open_case

		case = {
			"title": "Recovery suit against Acme",
			"case_type": "Litigation",
			"forum": "District Court",
			"case_number": "OS 41/2026",
			"filing_date": "2026-09-01",
			"company": TEST_COMPANY,
			"our_role": "Petitioner",
			"opposing_party": "Acme Traders",
		}
		with self.set_user(HOLDER):
			name = open_case(case, next_hearing="2027-01-20")["name"]
		saved = frappe.get_doc("Legal Case", name)
		self.assertEqual((saved.responsible, saved.status, saved.case_number), (HOLDER, "Open", "OS 41/2026"))
		self.assertEqual(str(saved.next_date), "2027-01-20")

	def test_starting_a_case_sets_only_what_the_form_offers(self):
		from kxcompliance.api import open_case

		with self.assertRaisesRegex(frappe.PermissionError, "cannot set status"):
			open_case({"title": "X", "status": "Settled"})
		with self.assertRaisesRegex(frappe.ValidationError, "single value"):
			open_case({"title": ["!=", ""]})
		with self.set_user(AUDITOR), self.assertRaises(frappe.PermissionError):
			open_case({"title": "X"})
