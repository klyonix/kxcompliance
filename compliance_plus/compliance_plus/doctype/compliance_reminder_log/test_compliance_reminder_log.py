# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Tests for the daily job in compliance_plus.compliance_plus.reminders."""

import frappe
from frappe.tests import IntegrationTestCase

from compliance_plus.compliance_plus.reminders import run_daily
from compliance_plus.compliance_plus.test_utils import (
	HOLDER,
	MANAGER,
	OTHER_HOLDER,
	REVIEWER,
	make_company,
	make_item,
	make_item_type,
	make_users,
)

# These tests build their own records; skip ERPNext's generated ones.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Compliance Task", "Legal Date"]

SETTINGS = "Compliance Plus Settings"


class TestReminderJob(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		make_item_type("Test Reminded Licence", grace=10, reminders=(30, 7))

	def setUp(self):
		frappe.db.delete("Compliance Reminder Log")
		# Quiet any items other tests left, so only this test's items can be reminded.
		frappe.db.set_value(
			"Compliance Item", {"is_cancelled": 0}, {"is_cancelled": 1, "status": "Cancelled"}
		)

	def logs(self, item=None, kind="Reminder"):
		filters = {"kind": kind}
		if item:
			filters["compliance_item"] = item
		return frappe.get_all("Compliance Reminder Log", filters=filters, fields=["rule_days", "sent_to"])

	def run_on(self, day):
		with self.freeze_time(day), self.change_settings(SETTINGS, enabled=1, digest_day="Monday"):
			run_daily()

	def test_one_reminder_for_the_nearest_rule_and_never_twice(self):
		with self.freeze_time("2026-06-01"):
			item = make_item("Test Reminded Licence", valid_until="2026-06-05").name
		self.run_on("2026-06-01")
		self.run_on("2026-06-01")
		logs = self.logs(item)
		self.assertEqual(len(logs), 1)
		self.assertEqual(logs[0].rule_days, 7)
		self.assertEqual(logs[0].sent_to, HOLDER)
		alerts = frappe.get_all(
			"Notification Log", filters={"document_type": "Compliance Item", "document_name": item}
		)
		self.assertEqual(len(alerts), 1)

	def test_nothing_is_sent_while_reminders_are_off_but_statuses_still_move(self):
		with self.freeze_time("2026-01-01"):
			item = make_item("Test Reminded Licence", valid_until="2026-06-20").name
		with self.freeze_time("2026-06-01"), self.change_settings(SETTINGS, enabled=0):
			run_daily()
		self.assertEqual(self.logs(item), [])
		self.assertEqual(frappe.db.get_value("Compliance Item", item, "status"), "Due for Renewal")

	def test_reminders_pause_while_a_renewal_is_applied(self):
		with self.freeze_time("2026-06-01"):
			item = make_item("Test Reminded Licence", valid_until="2026-06-05").name
			frappe.get_doc(
				{"doctype": "Compliance Renewal", "compliance_item": item, "status": "Applied"}
			).insert()
		self.run_on("2026-06-01")
		self.assertEqual(self.logs(item), [])

	def test_an_overdue_item_is_escalated_once_to_the_reviewer_and_managers(self):
		with self.freeze_time("2026-05-01"):
			item = make_item("Test Reminded Licence", valid_until="2026-05-10", reviewer=REVIEWER).name
		self.run_on("2026-05-20")
		self.run_on("2026-05-21")
		escalations = self.logs(item, kind="Escalation")
		self.assertEqual(len(escalations), 1)
		self.assertIn(REVIEWER, escalations[0].sent_to)
		self.assertIn(MANAGER, escalations[0].sent_to)

	def test_no_escalation_before_the_set_number_of_days(self):
		with self.freeze_time("2026-05-01"):
			item = make_item("Test Reminded Licence", valid_until="2026-05-10").name
		self.run_on("2026-05-12")
		self.assertEqual(self.logs(item, kind="Escalation"), [])

	def test_the_weekly_summary_goes_once_to_each_person_on_the_set_day(self):
		with self.freeze_time("2026-06-01"):
			make_item("Test Reminded Licence", valid_until="2026-06-10", responsible=HOLDER)
			make_item(
				"Test Reminded Licence", valid_until="2026-06-15", responsible=OTHER_HOLDER, reviewer=HOLDER
			)
		self.run_on("2026-06-02")  # a Tuesday
		self.assertEqual(self.logs(kind="Digest"), [])
		self.run_on("2026-06-01")  # a Monday
		self.run_on("2026-06-01")
		recipients = sorted(log.sent_to for log in self.logs(kind="Digest"))
		self.assertEqual(recipients, sorted([HOLDER, OTHER_HOLDER]))
