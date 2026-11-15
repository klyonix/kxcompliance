# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.install import APP_LOGO, set_branding


class TestBranding(IntegrationTestCase):
	def test_the_app_is_the_default_with_its_logo_unless_the_site_chose_its_own(self):
		frappe.db.set_single_value("System Settings", "default_app", None)
		frappe.db.set_single_value("Navbar Settings", "app_logo", None)
		set_branding()
		self.assertEqual(frappe.db.get_single_value("System Settings", "default_app"), "kxcompliance")
		self.assertEqual(frappe.db.get_single_value("Navbar Settings", "app_logo"), APP_LOGO)

		frappe.db.set_single_value("System Settings", "default_app", "erpnext")
		frappe.db.set_single_value("Navbar Settings", "app_logo", "/files/own-logo.png")
		set_branding()
		self.assertEqual(frappe.db.get_single_value("System Settings", "default_app"), "erpnext")
		self.assertEqual(frappe.db.get_single_value("Navbar Settings", "app_logo"), "/files/own-logo.png")
