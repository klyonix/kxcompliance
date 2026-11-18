# Copyright (c) 2025, KlyONIX Tech Consulting Pvt Ltd and Contributors
# See license.txt

import frappe

from kxcompliance.api import save_settings, settings_options
from kxcompliance.kx_compliance.test_utils import HOLDER, MANAGER, app_setting, make_company, make_users
from kxcompliance.testing import IntegrationTestCase

# These tests build their own records; skip ERPNext's generated ones.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Company", "User", "Email Account", "Email Template"]
test_ignore = IGNORE_TEST_RECORD_DEPENDENCIES  # the name Frappe 15 reads

SETTINGS = "KX Compliance Settings"


class TestKXComplianceSettings(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()

	def test_managers_change_the_apps_settings(self):
		with self.set_user(MANAGER):
			options = settings_options()
			self.assertIn("Monday", options["digest_days"])
			self.assertIn("CA/CS Firm", options["account_types"])
			saved = save_settings(
				{"enabled": 1, "due_soon_days": 45, "digest_day": "Friday", "app_name": "Rao & Associates"}
			)
		self.assertEqual((saved["due_soon_days"], saved["digest_day"]), (45, "Friday"))
		self.assertEqual(app_setting("app_name"), "Rao & Associates")

	def test_only_the_screens_fields_and_sensible_numbers_are_taken(self):
		with self.set_user(MANAGER):
			with self.assertRaises(frappe.ValidationError):
				save_settings({"setup_complete": 0})
			with self.assertRaises(frappe.ValidationError):
				save_settings({"due_soon_days": 0})
			with self.assertRaises(frappe.ValidationError):
				save_settings({"app_logo": "/private/files/logo.png"})

	def test_others_cannot_see_or_change_them(self):
		with self.set_user(HOLDER):
			with self.assertRaises(frappe.PermissionError):
				settings_options()
			with self.assertRaises(frappe.PermissionError):
				save_settings({"enabled": 0})
