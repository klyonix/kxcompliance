# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate

from compliance_plus.compliance_plus.report.compliance_cost.compliance_cost import execute as cost_report
from compliance_plus.compliance_plus.report.compliance_register.compliance_register import (
	execute as register_report,
)
from compliance_plus.compliance_plus.test_utils import (
	AUDITOR,
	HOLDER,
	OTHER_HOLDER,
	REVIEWER,
	TEST_COMPANY,
	make_company,
	make_file,
	make_item,
	make_item_type,
	make_users,
)

TODAY = "2026-06-01"


# These tests build their own records; skip ERPNext's generated ones.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Company", "Branch", "Supplier", "Currency", "Asset", "User"]


class TestComplianceItem(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		make_item_type("Test Expiring Licence", grace=10, reminders=(30, 7))
		make_item_type("Test Permanent Registration", cycle=0, reminders=())
		make_item_type("Test Certified Licence", requires_document=1)

	def status_on(self, valid_until, item_type="Test Expiring Licence", **fields):
		with self.freeze_time(TODAY):
			return make_item(item_type, valid_until=valid_until, **fields).status

	def test_status_follows_the_dates(self):
		self.assertEqual(self.status_on("2027-06-01"), "Active")
		self.assertEqual(self.status_on("2026-06-20"), "Due for Renewal")
		self.assertEqual(self.status_on("2026-05-25"), "Expired")
		self.assertEqual(self.status_on("2026-05-01"), "Lapsed")

	def test_an_item_that_does_not_expire_is_active(self):
		self.assertEqual(self.status_on(None, "Test Permanent Registration", days=None), "Active")

	def test_valid_until_is_required_for_a_type_that_expires(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Valid Until is required"):
			make_item("Test Expiring Licence", valid_until=None, days=None)

	def test_a_certificate_is_needed_before_an_item_is_active(self):
		self.assertEqual(self.status_on("2027-06-01", "Test Certified Licence"), "Draft")
		self.assertEqual(
			self.status_on("2027-06-01", "Test Certified Licence", certificate=make_file()), "Active"
		)

	def test_valid_from_cannot_be_after_valid_until(self):
		with self.assertRaisesRegex(frappe.ValidationError, "cannot be after Valid Until"):
			make_item("Test Expiring Licence", valid_from=add_days(getdate(), 400), days=200)

	def test_reminders_are_copied_from_the_type(self):
		item = make_item("Test Expiring Licence")
		self.assertEqual(sorted(rule.days_before for rule in item.reminders), [7, 30])

	def test_cleared_reminders_stay_cleared(self):
		item = make_item("Test Expiring Licence")
		item.reminders = []
		item.save()
		item.reload()
		self.assertEqual(item.reminders, [])

	def test_a_customer_or_supplier_holder_must_be_named(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Choose the Customer"):
			make_item("Test Expiring Licence", holder_type="Customer")

	def test_a_company_holder_is_the_company(self):
		item = make_item("Test Expiring Licence")
		self.assertEqual(item.holder_type, "Company")
		self.assertEqual(item.holder, TEST_COMPANY)

	def test_cancelling_needs_a_reason_and_happens_once(self):
		item = make_item("Test Expiring Licence")
		with self.assertRaisesRegex(frappe.ValidationError, "Give a reason"):
			item.cancel_item(reason="  ")
		item.cancel_item(reason="Branch closed")
		self.assertEqual(item.status, "Cancelled")
		self.assertEqual(item.cancellation_reason, "Branch closed")
		with self.assertRaisesRegex(frappe.ValidationError, "already cancelled"):
			item.cancel_item(reason="Again")

	def test_a_compliance_user_sees_only_items_they_hold_or_review(self):
		mine = make_item("Test Expiring Licence", responsible=HOLDER).name
		reviewed = make_item("Test Expiring Licence", responsible=OTHER_HOLDER, reviewer=HOLDER).name
		theirs = make_item("Test Expiring Licence", responsible=OTHER_HOLDER, reviewer=REVIEWER).name

		with self.set_user(HOLDER):
			visible = set(frappe.get_list("Compliance Item", pluck="name"))
			self.assertIn(mine, visible)
			self.assertIn(reviewed, visible)
			self.assertNotIn(theirs, visible)
			self.assertFalse(frappe.has_permission("Compliance Item", "read", theirs))

	def test_an_auditor_reads_everything_and_writes_nothing(self):
		item = make_item("Test Expiring Licence", responsible=OTHER_HOLDER).name
		with self.set_user(AUDITOR):
			self.assertTrue(frappe.has_permission("Compliance Item", "read", item))
			self.assertFalse(frappe.has_permission("Compliance Item", "write", item))

	def test_the_register_report_lists_only_what_the_user_may_see(self):
		mine = make_item("Test Expiring Licence", responsible=HOLDER).name
		theirs = make_item("Test Expiring Licence", responsible=OTHER_HOLDER).name
		with self.set_user(HOLDER):
			_columns, rows = register_report({"company": TEST_COMPANY})
		names = {row.name for row in rows}
		self.assertIn(mine, names)
		self.assertNotIn(theirs, names)

	def test_the_cost_report_gives_a_yearly_figure(self):
		make_item_type("Test Costed Subscription", reminders=())
		make_item("Test Costed Subscription", cost=1000, billing_cycle="Monthly")
		make_item("Test Costed Subscription", cost=5000, billing_cycle="Yearly")
		_columns, rows = cost_report({"company": TEST_COMPANY})
		row = next(row for row in rows if row.item_type == "Test Costed Subscription")
		self.assertEqual(row.item_count, 2)
		self.assertEqual(row.annual_cost, 17000)

	def test_the_app_offers_active_types_states_and_people(self):
		from compliance_plus.api import item_form_options
		from compliance_plus.compliance_plus.test_utils import HOLDER, MANAGER

		with self.set_user(HOLDER):
			options = item_form_options()
		self.assertIn("Test Expiring Licence", [row.name for row in options["item_types"]])
		self.assertIn("Karnataka", options["states"])
		self.assertIn(MANAGER, [row.name for row in options["people"]])
