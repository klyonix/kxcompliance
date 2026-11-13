# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.tests import IntegrationTestCase

from compliance_plus.api import my_work, save_changes
from compliance_plus.compliance_plus.test_utils import (
	HOLDER,
	MANAGER,
	OTHER_HOLDER,
	REVIEWER,
	TEST_COMPANY,
	make_company,
	make_item,
	make_item_type,
	make_user,
	make_users,
)
from compliance_plus.www import compliance_manifest

OUTSIDER = "compliance-outsider@example.com"


class TestAppApi(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		make_user(OUTSIDER, ("Accounts User",))
		make_item_type("Test App Licence", grace=10, reminders=(30,))

	def test_my_work_lists_only_what_the_person_holds_or_reviews(self):
		mine = make_item("Test App Licence", days=10, responsible=HOLDER).name
		reviewing = make_item("Test App Licence", days=12, responsible=OTHER_HOLDER, reviewer=HOLDER).name
		theirs = make_item("Test App Licence", days=11, responsible=OTHER_HOLDER, reviewer=MANAGER).name
		with self.set_user(HOLDER):
			names = {item.name for item in my_work()["items"]}
		self.assertTrue({mine, reviewing} <= names)
		self.assertNotIn(theirs, names)

	def test_my_work_needs_a_compliance_role(self):
		with self.set_user(OUTSIDER), self.assertRaises(frappe.PermissionError):
			my_work()

	def test_save_changes_saves_allowed_fields_on_the_persons_own_record(self):
		item = make_item("Test App Licence", responsible=HOLDER)
		with self.set_user(HOLDER):
			result = save_changes(
				"Compliance Item", item.name, {"reference_number": "TL/2026/77"}, str(item.modified)
			)
		self.assertEqual(frappe.db.get_value("Compliance Item", item.name, "reference_number"), "TL/2026/77")
		self.assertTrue(result["modified"])

	def test_save_changes_refuses_fields_and_records_outside_the_app(self):
		item = make_item("Test App Licence", responsible=HOLDER)
		with self.set_user(HOLDER):
			with self.assertRaisesRegex(frappe.PermissionError, "valid_until"):
				save_changes("Compliance Item", item.name, {"valid_until": "2099-01-01"})
			with self.assertRaisesRegex(frappe.PermissionError, "cannot change"):
				save_changes("Compliance Obligation Template", "GSTR-1 (Monthly)", {"due_day": 1})

	def test_save_changes_refuses_another_persons_record(self):
		theirs = make_item("Test App Licence", responsible=OTHER_HOLDER, reviewer=MANAGER)
		with self.set_user(HOLDER), self.assertRaises(frappe.PermissionError):
			save_changes("Compliance Item", theirs.name, {"notes": "mine now"})

	def test_save_changes_refuses_a_change_made_on_an_older_copy(self):
		item = make_item("Test App Licence", responsible=HOLDER)
		stale = str(item.modified)
		item.notes = "Changed by someone else"
		item.save()
		with self.set_user(HOLDER), self.assertRaises(frappe.TimestampMismatchError):
			save_changes("Compliance Item", item.name, {"notes": "Offline note"}, stale)

	def test_the_manifest_carries_the_sites_name_and_logo(self):
		with self.change_settings(
			"Compliance Plus Settings", app_name="Acme Compliance", app_logo="/files/acme.png"
		):
			manifest = json.loads(compliance_manifest.get_context(frappe._dict())["manifest"])
		self.assertEqual(manifest["name"], "Acme Compliance")
		self.assertEqual(manifest["start_url"], "/compliance")
		self.assertEqual(manifest["icons"][0]["src"], "/files/acme.png")

	def test_the_app_logo_must_be_public(self):
		settings = frappe.get_doc("Compliance Plus Settings")
		settings.app_logo = "/private/files/logo.png"
		with self.assertRaisesRegex(frappe.ValidationError, "public file"):
			settings.save()
