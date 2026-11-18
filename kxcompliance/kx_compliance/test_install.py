# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe

from kxcompliance.install import APP_LOGO, CLIENT_ROLE, keep_client_role_off_desk, set_branding
from kxcompliance.testing import IntegrationTestCase


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


class TestClientRole(IntegrationTestCase):
	def test_a_client_login_is_kept_off_the_desk_even_if_the_role_was_made_with_it(self):
		login = "role-test-client@example.com"
		if not frappe.db.exists("User", login):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": login,
					"first_name": "Role Test",
					"send_welcome_email": 0,
					"roles": [{"role": CLIENT_ROLE}],
				}
			).insert()
		role = frappe.get_doc("Role", CLIENT_ROLE)
		role.desk_access = 1
		role.save()
		self.assertEqual(frappe.db.get_value("User", login, "user_type"), "System User")
		keep_client_role_off_desk()
		self.assertEqual(frappe.db.get_value("Role", CLIENT_ROLE, "desk_access"), 0)
		self.assertEqual(frappe.db.get_value("User", login, "user_type"), "Website User")
