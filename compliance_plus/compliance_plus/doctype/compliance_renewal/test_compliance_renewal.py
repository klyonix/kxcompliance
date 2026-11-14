# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from compliance_plus.compliance_plus.test_utils import (
	HOLDER,
	MANAGER,
	OTHER_HOLDER,
	make_company,
	make_file,
	make_item,
	make_item_type,
	make_users,
)

# These tests build their own records; skip ERPNext's generated ones.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Purchase Invoice"]


class TestComplianceRenewal(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		make_item_type("Test Renewable Licence", requires_document=1)

	def setUp(self):
		self.old_certificate = make_file("old.txt")
		self.item = make_item(
			"Test Renewable Licence",
			valid_from="2026-01-01",
			valid_until="2026-12-31",
			certificate=self.old_certificate,
		)

	def renewal(self, **fields):
		return frappe.get_doc(
			{"doctype": "Compliance Renewal", "compliance_item": self.item.name, **fields}
		).insert()

	def test_an_applied_renewal_marks_the_item_in_progress(self):
		renewal = self.renewal()
		renewal.status = "Applied"
		renewal.save()
		self.assertEqual(
			frappe.db.get_value("Compliance Item", self.item.name, "status"), "Renewal in Progress"
		)
		self.assertTrue(renewal.applied_on)

	def test_approving_moves_the_dates_and_keeps_the_old_certificate(self):
		new_certificate = make_file("new.txt")
		renewal = self.renewal(status="Applied")
		renewal.update(
			{
				"status": "Approved",
				"new_valid_from": "2027-01-01",
				"new_valid_until": "2027-12-31",
				"new_certificate": new_certificate,
			}
		)
		with self.set_user(MANAGER):
			renewal.save()

		item = frappe.get_doc("Compliance Item", self.item.name)
		self.assertEqual(str(item.valid_until), "2027-12-31")
		self.assertEqual(item.certificate, new_certificate)
		self.assertEqual(renewal.previous_certificate, self.old_certificate)
		self.assertEqual(str(renewal.previous_valid_until), "2026-12-31")
		self.assertNotEqual(item.status, "Renewal in Progress")

	def test_only_a_manager_approves(self):
		renewal = self.renewal(status="Applied")
		renewal.update(
			{"status": "Approved", "new_valid_until": "2027-12-31", "new_certificate": make_file()}
		)
		with self.set_user(HOLDER), self.assertRaises(frappe.PermissionError):
			renewal.save()

	def test_approval_needs_a_later_date_and_a_certificate(self):
		renewal = self.renewal(status="Applied")
		renewal.update({"status": "Approved", "new_valid_until": "2027-12-31"})
		with self.assertRaisesRegex(frappe.ValidationError, "New Certificate"):
			renewal.save()
		renewal = frappe.get_doc("Compliance Renewal", renewal.name)
		renewal.update(
			{"status": "Approved", "new_valid_until": "2026-06-30", "new_certificate": make_file()}
		)
		with self.assertRaisesRegex(frappe.ValidationError, "must be after the current Valid Until"):
			renewal.save()

	def test_one_open_renewal_per_item(self):
		self.renewal()
		with self.assertRaisesRegex(frappe.ValidationError, "already has an open renewal"):
			self.renewal()

	def test_a_closed_renewal_cannot_reopen(self):
		renewal = self.renewal()
		renewal.status = "Withdrawn"
		renewal.save()
		renewal.status = "Applied"
		with self.assertRaisesRegex(frappe.ValidationError, "cannot change"):
			renewal.save()

	def test_a_cancelled_item_cannot_be_renewed(self):
		self.item.cancel_item(reason="Closed")
		with self.assertRaisesRegex(frappe.ValidationError, "cannot be renewed"):
			self.renewal()

	def test_a_compliance_user_sees_renewals_only_of_their_items(self):
		renewal = self.renewal().name
		with self.set_user(OTHER_HOLDER):
			self.assertNotIn(renewal, frappe.get_list("Compliance Renewal", pluck="name"))
			self.assertFalse(frappe.has_permission("Compliance Renewal", "read", renewal))
		with self.set_user(HOLDER):
			self.assertIn(renewal, frappe.get_list("Compliance Renewal", pluck="name"))

	def test_the_app_records_and_completes_a_renewal(self):
		from compliance_plus.api import save_changes

		renewal = self.renewal(status="Applied")
		new_certificate = make_file("renewed.txt")
		with self.set_user(HOLDER):
			save_changes(
				"Compliance Renewal",
				renewal.name,
				{"new_valid_until": "2027-12-31", "new_certificate": new_certificate, "fee": 2500},
			)
			with self.assertRaises(frappe.PermissionError):
				save_changes("Compliance Renewal", renewal.name, {"status": "Approved"})
			with self.assertRaises(frappe.PermissionError):
				save_changes("Compliance Renewal", renewal.name, {"previous_valid_until": "2020-01-01"})
		with self.set_user(MANAGER):
			save_changes("Compliance Renewal", renewal.name, {"status": "Approved"})
		item = frappe.get_doc("Compliance Item", self.item.name)
		self.assertEqual((str(item.valid_until), item.certificate), ("2027-12-31", new_certificate))
