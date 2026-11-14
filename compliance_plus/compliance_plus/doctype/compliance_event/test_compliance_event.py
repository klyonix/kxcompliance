# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from compliance_plus.api import event_types
from compliance_plus.compliance_plus.company_events import event_type_query, event_types_for
from compliance_plus.compliance_plus.doctype.compliance_task.test_compliance_task import (
	make_profile,
	obligation,
)
from compliance_plus.compliance_plus.statutory import generate_tasks
from compliance_plus.compliance_plus.test_utils import (
	HOLDER,
	MANAGER,
	REVIEWER,
	TEST_COMPANY,
	make_company,
	make_users,
)

# These tests build their own records; skip ERPNext's generated ones.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Company", "User"]


def record(event_type: str, event_date: str = "2026-11-10", **fields):
	return frappe.get_doc(
		{
			"doctype": "Compliance Event",
			"company": TEST_COMPANY,
			"event_type": event_type,
			"event_date": event_date,
			"description": fields.pop("description", "Asha Rao appointed as an additional director"),
			**fields,
		}
	).insert()


def event_tasks(event) -> list:
	return frappe.get_all(
		"Compliance Task",
		filters={"company_event": event.name},
		fields=["name", "obligation_template", "due_date", "status", "responsible", "reviewer", "is_overdue"],
	)


class TestComplianceEvent(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()

	def setUp(self):
		# Data stays until the class ends, so clear what an earlier test may have left.
		frappe.db.delete("Compliance Task")
		frappe.db.delete("Compliance Event")
		make_profile()

	def test_a_change_in_directors_makes_dir_12_due_in_30_days(self):
		with self.freeze_time("2026-11-15"), self.set_user(HOLDER):
			event = record("Change in Directors")
		tasks = event_tasks(event)
		self.assertEqual([task.obligation_template for task in tasks], ["DIR-12 (Change in Directors)"])
		self.assertEqual(str(tasks[0].due_date), "2026-12-10")
		self.assertEqual((tasks[0].responsible, tasks[0].reviewer), (HOLDER, REVIEWER))
		self.assertEqual(event.recorded_by, HOLDER)

	def test_forms_follow_the_kind_of_company(self):
		with self.freeze_time("2026-11-15"):
			# A private company has no partners: the event is refused, not recorded with nothing due.
			with self.assertRaisesRegex(frappe.ValidationError, "calls for no filing"):
				record("Partner Changed")
			make_profile("LLP")
			self.assertEqual(
				[task.obligation_template for task in event_tasks(record("Partner Changed"))],
				["LLP Form 4 (Partner Changed)"],
			)

	def test_only_events_that_call_for_a_filing_are_offered(self):
		company_events = event_types_for("Private Limited")
		self.assertIn("Change in Directors", company_events)
		self.assertNotIn("Partner Changed", company_events)
		llp_events = event_types_for("LLP")
		self.assertEqual(llp_events, ["LLP Agreement Changed", "Partner Changed"])
		with self.set_user(HOLDER):
			offered = [row.name for row in event_types(TEST_COMPANY)]
			picker = [
				row[0]
				for row in event_type_query(
					"Compliance Event Type", "", "name", 0, 50, {"company": TEST_COMPANY}
				)
			]
		self.assertEqual(offered, company_events)
		self.assertEqual(picker, company_events)

	def test_an_event_recorded_late_is_overdue_at_once(self):
		with self.freeze_time("2026-11-15"):
			event = record(
				"Resolution to be Filed", "2026-09-01", description="Special resolution to alter the articles"
			)
		self.assertEqual(event_tasks(event)[0].is_overdue, 1)

	def test_future_events_and_companies_without_a_profile_are_refused(self):
		with self.freeze_time("2026-11-15"):
			with self.assertRaisesRegex(frappe.ValidationError, "once it has happened"):
				record("Change in Directors", "2026-12-01")
			frappe.delete_doc("Company Compliance Profile", TEST_COMPANY, force=True)
			with self.assertRaisesRegex(frappe.ValidationError, "Company Compliance Profile"):
				record("Change in Directors")

	def test_only_a_manager_cancels_an_event_and_its_open_filings(self):
		with self.freeze_time("2026-11-15"):
			with self.set_user(HOLDER):
				event = record("Charge Created or Modified", description="Term loan from State Bank of India")
				with self.assertRaises(frappe.PermissionError):
					event.cancel_event("Recorded twice")
			with self.set_user(MANAGER):
				event.reload()
				event.cancel_event("Recorded twice")
		self.assertEqual(event.status, "Cancelled")
		self.assertEqual({task.status for task in event_tasks(event)}, {"Cancelled"})

	def test_event_forms_are_not_standing_obligations(self):
		profile = make_profile(obligations=[obligation("DIR-12 (Change in Directors)")])
		with self.set_user(MANAGER):
			profile.find_obligations()
		self.assertFalse(
			{"INC-20A (Commencement of Business)", "MGT-14 (Filing of Resolutions)"}
			& {row.obligation_template for row in profile.obligations}
		)
		with self.freeze_time("2026-11-15"):
			generate_tasks(company=TEST_COMPANY)
		self.assertFalse(
			frappe.db.exists("Compliance Task", {"obligation_template": "DIR-12 (Change in Directors)"})
		)
