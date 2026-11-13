# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from compliance_plus.compliance_plus.move_old_trackers import move_all, move_doctype
from compliance_plus.compliance_plus.test_utils import (
	HOLDER,
	TEST_COMPANY,
	make_company,
	make_file,
	make_users,
)


def old_row(doctype: str, **fields):
	values = {
		"doctype": doctype,
		"document_name": "Old record",
		"issuer_supplier": "Municipal Corporation",
		"status": "Active",
		"issue_date": "2026-01-01",
		"expiry_date": "2027-01-01",
	}
	values.update(fields)
	return frappe.get_doc(values).insert(ignore_permissions=True)


def moved(doctype: str, name: str):
	item = frappe.db.get_value("Compliance Item", {"source_doctype": doctype, "source_name": name}, "name")
	return frappe.get_doc("Compliance Item", item) if item else None


class TestMoveOldTrackers(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()

	def setUp(self):
		frappe.defaults.set_global_default("company", TEST_COMPANY)

	def test_a_licence_row_moves_with_its_dates_reminder_and_notes(self):
		row = old_row(
			"Licence Tracker",
			document_name="Pune trade licence",
			type="Trade",
			in_charge=HOLDER,
			enable_reminder=1,
			remind_before_days=45,
		)
		move_doctype("Licence Tracker")
		item = moved("Licence Tracker", row.name)

		self.assertEqual(item.title, "Pune trade licence")
		self.assertEqual(item.item_type, "Licence")
		self.assertEqual(item.issuing_authority, "Municipal Corporation")
		self.assertEqual(str(item.valid_until), "2027-01-01")
		self.assertEqual(item.responsible, HOLDER)
		self.assertEqual([rule.days_before for rule in item.reminders], [45])
		self.assertIn("Trade", item.notes)
		self.assertIn("Status before the move", item.notes)

	def test_a_compliance_tracker_row_takes_its_category_as_the_type(self):
		if not frappe.db.exists("Compliance Category", "Labour Law"):
			frappe.get_doc({"doctype": "Compliance Category", "category_name": "Labour Law"}).insert()
		row = old_row("Compliance Tracker", compliance_category="Labour Law")
		move_doctype("Compliance Tracker")
		item = moved("Compliance Tracker", row.name)
		self.assertEqual(item.item_type, "Labour Law")
		self.assertEqual(frappe.db.get_value("Compliance Item Type", "Labour Law", "category"), "Other")

	def test_a_subscription_row_moves_its_period_and_billing_cycle(self):
		row = old_row(
			"Subscription Tracker",
			issue_date=None,
			expiry_date=None,
			start_date="2026-04-01",
			end_date="2027-03-31",
			subscription_type="Monthly",
		)
		move_doctype("Subscription Tracker")
		item = moved("Subscription Tracker", row.name)
		self.assertEqual(str(item.valid_from), "2026-04-01")
		self.assertEqual(str(item.valid_until), "2027-03-31")
		self.assertEqual(item.billing_cycle, "Monthly")
		self.assertEqual(item.item_type, "Subscription")

	def test_running_again_moves_nothing_twice(self):
		row = old_row("Insurance Tracker", agent_name="A. Agent")
		first = move_doctype("Insurance Tracker")
		second = move_doctype("Insurance Tracker")
		self.assertEqual(second["moved"], 0)
		self.assertEqual(second["already_moved"], first["moved"] + first["already_moved"])
		self.assertEqual(
			frappe.db.count(
				"Compliance Item", {"source_doctype": "Insurance Tracker", "source_name": row.name}
			),
			1,
		)
		self.assertIn("A. Agent", moved("Insurance Tracker", row.name).notes)

	def test_a_row_that_cannot_move_is_counted_and_does_not_stop_the_rest(self):
		bad = old_row("Licence Tracker", issue_date="2027-06-01", expiry_date="2027-01-01")
		good = old_row("Licence Tracker")
		counts = move_doctype("Licence Tracker")
		self.assertGreaterEqual(counts["failed"], 1)
		self.assertIsNone(moved("Licence Tracker", bad.name))
		self.assertIsNotNone(moved("Licence Tracker", good.name))
		self.assertTrue(frappe.db.exists("Licence Tracker", bad.name))

	def test_attachments_are_linked_to_the_new_item(self):
		row = old_row("Licence Tracker")
		file_url = make_file("licence.txt")
		frappe.db.set_value(
			"File",
			{"file_url": file_url},
			{"attached_to_doctype": "Licence Tracker", "attached_to_name": row.name},
		)
		move_doctype("Licence Tracker")
		item = moved("Licence Tracker", row.name)
		self.assertTrue(
			frappe.db.exists(
				"File",
				{
					"attached_to_doctype": "Compliance Item",
					"attached_to_name": item.name,
					"file_url": file_url,
				},
			)
		)

	def test_without_someone_in_charge_the_owner_is_responsible(self):
		row = old_row("Licence Tracker", in_charge=None)
		move_doctype("Licence Tracker")
		self.assertEqual(moved("Licence Tracker", row.name).responsible, row.owner)

	def test_move_all_covers_the_four_trackers(self):
		self.assertEqual(
			set(move_all()),
			{"Compliance Tracker", "Licence Tracker", "Insurance Tracker", "Subscription Tracker"},
		)

	def test_several_companies_and_no_default_stop_the_move(self):
		old_row("Licence Tracker")
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "Second Compliance Company",
				"abbr": "SCC",
				"default_currency": "INR",
				"country": "India",
			}
		).insert()
		with patch("frappe.defaults.get_global_default", return_value=None):
			with self.assertRaisesRegex(frappe.ValidationError, "Set a default company"):
				move_doctype("Licence Tracker")
