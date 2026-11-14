# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from compliance_plus.compliance_plus.statutory import generate_tasks, run_daily
from compliance_plus.compliance_plus.test_utils import (
	HOLDER,
	MANAGER,
	OTHER_HOLDER,
	REVIEWER,
	TEST_COMPANY,
	make_company,
	make_file,
	make_users,
)

# These tests build their own records; skip ERPNext's generated ones.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Company", "User"]

SETTINGS = "Compliance Plus Settings"


def make_profile(company_type: str = "Private Limited", **fields):
	if frappe.db.exists("Company Compliance Profile", TEST_COMPANY):
		frappe.delete_doc("Company Compliance Profile", TEST_COMPANY, force=True)
	return frappe.get_doc(
		{
			"doctype": "Company Compliance Profile",
			"company": TEST_COMPANY,
			"company_type": company_type,
			"default_responsible": HOLDER,
			"default_reviewer": REVIEWER,
			**fields,
		}
	).insert()


def obligation(template: str, start_from: str = "2026-10-01", **fields):
	return {
		"obligation_template": template,
		"responsible": HOLDER,
		"reviewer": REVIEWER,
		"start_from": start_from,
		**fields,
	}


def tasks(template: str | None = None, **filters):
	if template:
		filters["obligation_template"] = template
	return frappe.get_all(
		"Compliance Task",
		filters={"company": TEST_COMPANY, **filters},
		fields=["name", "period_label", "due_date", "effective_due_date", "status"],
		order_by="period_end asc",
	)


class TestComplianceTask(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()

	def setUp(self):
		# Data stays until the class ends, so clear what an earlier test may have left.
		frappe.db.delete("Compliance Task", {"company": TEST_COMPANY})
		frappe.db.delete("Compliance Due Date Extension")

	def test_finding_obligations_follows_type_registrations_and_states(self):
		profile = make_profile(
			registrations=[
				{"registration_type": "GST", "registration_number": "29ABCDE1234F1Z5", "state": "Karnataka"},
				{"registration_type": "TAN", "registration_number": "BLRA12345B"},
				{"registration_type": "PT", "registration_number": "PTKA001", "state": "Karnataka"},
			]
		)
		with self.set_user(MANAGER):
			profile.find_obligations()
		found = {row.obligation_template for row in profile.obligations}
		self.assertTrue(
			{
				"GSTR-3B (Monthly)",
				"TDS/TCS Payment",
				"Professional Tax - Karnataka",
				"AOC-4 (Financial Statements)",
			}
			<= found
		)
		for absent in (
			"GSTR-3B (QRMP, 22nd)",
			"PF ECR and Payment",
			"Professional Tax - Maharashtra",
			"LLP Form 11 (Annual Return)",
		):
			self.assertNotIn(absent, found)
		gst = next(row for row in profile.obligations if row.obligation_template == "GSTR-3B (Monthly)")
		self.assertEqual(gst.registration_number, "29ABCDE1234F1Z5")
		with self.set_user(MANAGER):
			self.assertEqual(profile.find_obligations(), 0)

	def test_a_composition_proprietor_gets_its_own_filings(self):
		profile = make_profile(
			"Proprietorship",
			registrations=[
				{
					"registration_type": "GST Composition",
					"registration_number": "33ABCDE1234F1Z5",
					"state": "Tamil Nadu",
				},
				{"registration_type": "IEC", "registration_number": "ABCDE1234F"},
			],
		)
		with self.set_user(MANAGER):
			profile.find_obligations()
		found = {row.obligation_template for row in profile.obligations}
		self.assertTrue(
			{
				"CMP-08 (Composition Payment)",
				"GSTR-4 (Composition Annual Return)",
				"Income Tax Return (Proprietor, Non-audit)",
				"IEC Annual Update",
				"Advance Tax",
			}
			<= found
		)
		for absent in (
			"GSTR-1 (Monthly)",
			"GSTR-3B (Monthly)",
			"GSTR-9 (Annual Return)",
			"Income Tax Return (Audit Cases)",
			"Income Tax Return (Proprietor, Audit Cases)",
			"AOC-4 (Financial Statements)",
			"Shareholding Pattern",
		):
			self.assertNotIn(absent, found)

	def test_a_listed_company_gets_its_sebi_filings(self):
		profile = make_profile(
			"Public Limited",
			registrations=[{"registration_type": "Stock Exchange", "registration_number": "NSE: DEMOCO"}],
		)
		with self.set_user(MANAGER):
			profile.find_obligations()
		found = {row.obligation_template for row in profile.obligations}
		self.assertTrue(
			{"Shareholding Pattern", "Integrated Filing (Governance)", "Integrated Filing (Financial)"}
			<= found
		)

	def test_tasks_are_made_up_to_the_horizon_and_never_twice(self):
		make_profile(obligations=[obligation("GSTR-3B (Monthly)", registration_number="29GST")])
		with self.change_settings(SETTINGS, generation_horizon_days=45):
			made = generate_tasks(company=TEST_COMPANY, today="2026-11-20")
			again = generate_tasks(company=TEST_COMPANY, today="2026-11-20")
		self.assertEqual(made, 3)
		self.assertEqual(again, 0)
		rows = tasks("GSTR-3B (Monthly)")
		self.assertEqual([row.period_label for row in rows], ["Oct 2026", "Nov 2026", "Dec 2026"])
		self.assertEqual(str(rows[0].due_date), "2026-11-20")

	def test_an_inactive_obligation_makes_nothing(self):
		make_profile(obligations=[obligation("GSTR-3B (Monthly)", is_active=0)])
		self.assertEqual(generate_tasks(company=TEST_COMPANY, today="2026-11-20"), 0)

	def test_filings_after_the_agm_wait_for_its_date(self):
		profile = make_profile(
			obligations=[obligation("AOC-4 (Financial Statements)", start_from="2026-04-01")]
		)
		self.assertEqual(generate_tasks(company=TEST_COMPANY, today="2027-09-01"), 0)
		profile.append("agm_dates", {"financial_year_end": "2027-03-31", "agm_date": "2027-09-10"})
		profile.save()
		generate_tasks(company=TEST_COMPANY, today="2027-09-15")
		rows = tasks("AOC-4 (Financial Statements)")
		self.assertEqual(len(rows), 1)
		self.assertEqual(str(rows[0].due_date), "2027-10-10")
		self.assertEqual(rows[0].period_label, "FY 2026-27")

	def make_task(self, template="GSTR-3B (Monthly)", today="2026-11-05"):
		make_profile(obligations=[obligation(template, registration_number="29GST")])
		with self.change_settings(SETTINGS, generation_horizon_days=0):
			generate_tasks(company=TEST_COMPANY, today=today)
		return frappe.get_doc("Compliance Task", tasks(template)[0].name)

	def file(self, task, filed_on="2026-11-18"):
		task.update(
			{"filed_on": filed_on, "acknowledgement_number": "AA2911260000001", "proof": make_file("ack.txt")}
		)

	def test_ready_for_review_needs_the_filing_details(self):
		task = self.make_task()
		task.status = "Ready for Review"
		with self.assertRaisesRegex(frappe.ValidationError, "Filed On.*Acknowledgement Number.*Proof"):
			task.save()

	def test_the_preparer_cannot_mark_their_own_filing_filed(self):
		# A Compliance Manager may file anyone else's task, but not one they prepared.
		task = self.make_task()
		task.responsible = MANAGER
		self.file(task)
		task.status = "Ready for Review"
		task.save()
		task.status = "Filed"
		with (
			self.set_user(MANAGER),
			self.assertRaisesRegex(frappe.PermissionError, "someone else must check"),
		):
			task.save()

	def test_the_reviewer_files_and_late_filing_is_marked(self):
		task = self.make_task()
		self.file(task, filed_on="2026-11-18")
		task.status = "Filed"
		with self.set_user(REVIEWER):
			task.save()
		self.assertEqual(task.status, "Filed")
		self.assertEqual(task.reviewed_by, REVIEWER)

		late = frappe.get_doc("Compliance Task", tasks("GSTR-3B (Monthly)")[0].name)
		late.db_set("status", "Open")
		late.reload()
		self.file(late, filed_on="2026-11-25")
		late.status = "Filed"
		with self.set_user(MANAGER):
			late.save()
		self.assertEqual(late.status, "Filed Late")

	def test_not_applicable_needs_a_reason_and_a_closed_task_stays_closed(self):
		task = self.make_task()
		task.status = "Not Applicable"
		with self.assertRaisesRegex(frappe.ValidationError, "Remarks"):
			task.save()
		task = frappe.get_doc("Compliance Task", task.name)
		task.status = "Not Applicable"
		task.remarks = "No supplies this month"
		task.save()
		task.status = "Open"
		with self.set_user(HOLDER), self.assertRaises(frappe.PermissionError):
			task.save()

	def test_an_extension_moves_open_tasks_and_leaves_filed_ones(self):
		make_profile(
			obligations=[
				obligation("GSTR-3B (Monthly)", registration_number="29GST", start_from="2026-09-01")
			]
		)
		with self.change_settings(SETTINGS, generation_horizon_days=0):
			generate_tasks(company=TEST_COMPANY, today="2026-11-05")
		september, october = (
			frappe.get_doc("Compliance Task", row.name) for row in tasks("GSTR-3B (Monthly)")
		)
		self.file(september, filed_on="2026-10-18")
		september.status = "Filed"
		with self.set_user(REVIEWER):
			september.save()

		frappe.get_doc(
			{
				"doctype": "Compliance Due Date Extension",
				"obligation_template": "GSTR-3B (Monthly)",
				"periods_ending_from": "2026-09-01",
				"periods_ending_to": "2026-10-31",
				"new_due_date": "2026-11-30",
				"notification_reference": "Test notification 1/2026",
			}
		).insert()
		september.reload()
		october.reload()
		self.assertIsNone(september.extended_due_date)
		self.assertEqual(str(october.effective_due_date), "2026-11-30")

	def test_a_compliance_user_sees_only_their_tasks(self):
		make_profile(
			obligations=[
				obligation("GSTR-3B (Monthly)", registration_number="mine"),
				obligation(
					"GSTR-1 (Monthly)",
					registration_number="theirs",
					responsible=OTHER_HOLDER,
					reviewer=MANAGER,
				),
			]
		)
		generate_tasks(company=TEST_COMPANY, today="2026-11-05")
		mine = tasks("GSTR-3B (Monthly)")[0].name
		theirs = tasks("GSTR-1 (Monthly)")[0].name
		with self.set_user(HOLDER):
			visible = set(frappe.get_list("Compliance Task", pluck="name"))
		self.assertIn(mine, visible)
		self.assertNotIn(theirs, visible)

	def test_task_reminders_and_escalations_go_once(self):
		self.make_task()

		def logs(kind):
			return frappe.get_all(
				"Compliance Reminder Log", filters={"kind": kind, "compliance_task": ("is", "set")}
			)

		frappe.db.delete("Compliance Reminder Log")
		with self.change_settings(SETTINGS, enabled=1, generation_horizon_days=0, escalate_after_days=3):
			for day in ("2026-11-18", "2026-11-18"):
				with self.freeze_time(day):
					run_daily()
			self.assertEqual(len(logs("Reminder")), 1)
			for day in ("2026-11-24", "2026-11-25"):
				with self.freeze_time(day):
					run_daily()
		self.assertEqual(len(logs("Escalation")), 1)
		self.assertTrue(frappe.db.get_value("Compliance Task", tasks()[0].name, "is_overdue"))

	def test_a_compliance_user_cannot_move_their_own_due_date(self):
		task = self.make_task()
		task.due_date = "2026-12-31"
		with (
			self.set_user(HOLDER),
			self.assertRaisesRegex(frappe.PermissionError, "Due Date cannot be changed"),
		):
			task.save()

	def test_an_extension_made_first_applies_to_tasks_made_later(self):
		frappe.get_doc(
			{
				"doctype": "Compliance Due Date Extension",
				"obligation_template": "GSTR-3B (Monthly)",
				"periods_ending_from": "2026-10-01",
				"periods_ending_to": "2026-10-31",
				"new_due_date": "2026-11-27",
				"notification_reference": "Test notification 2/2026",
			}
		).insert()
		task = self.make_task()
		self.assertEqual(str(task.effective_due_date), "2026-11-27")
