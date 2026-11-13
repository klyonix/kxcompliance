# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from compliance_plus.compliance_plus.custom.license_tracker_cron import send_license_expiry_reminders


class TestLicenseTrackerCron(IntegrationTestCase):
	def test_a_site_without_customer_licence_tables_logs_no_error(self):
		self.assertFalse(frappe.db.exists("DocType", "Drug License Details"))
		before = frappe.db.count("Error Log")
		send_license_expiry_reminders()
		self.assertEqual(frappe.db.count("Error Log"), before)
