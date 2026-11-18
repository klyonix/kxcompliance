# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import re
from pathlib import Path
from urllib.parse import urlparse

import frappe

from kxcompliance.kx_compliance.app_links import LISTS, PAGES, app_path, app_url
from kxcompliance.kx_compliance.test_utils import HOLDER, make_users
from kxcompliance.testing import IntegrationTestCase

ROUTER = Path(__file__).resolve().parents[2] / "frontend" / "src" / "router.js"


class TestAppLinks(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_users()

	def test_every_link_is_a_page_of_the_app(self):
		paths = set(re.findall(r'path: "([^"]+)"', ROUTER.read_text()))
		for template in [*PAGES.values(), *LISTS.values()]:
			route = "/" + template.replace("{name}", ":name")
			self.assertIn(route, paths, template)

	def test_a_record_opens_in_the_app_and_others_in_the_desk(self):
		self.assertEqual(app_path("Compliance Task", "CT-26-00004"), "/compliance/filings/CT-26-00004")
		self.assertEqual(app_path("Legal Date", "LD-1"), "/compliance/legal")
		self.assertTrue(app_url("Compliance Item", "CI 1/2").endswith("/compliance/register/CI%201%2F2"))
		desk = app_url("Sales Invoice", "SINV-1")
		self.assertIn("sales-invoice/SINV-1", desk)
		self.assertFalse(urlparse(desk).path.startswith("/compliance"))

	def test_a_notification_email_links_to_the_app(self):
		log = frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": HOLDER,
				"type": "Alert",
				"subject": "Test",
				"document_type": "Compliance Task",
				"document_name": "CT-TEST-1",
			}
		).insert(ignore_permissions=True)
		self.assertTrue(log.link.endswith("/compliance/filings/CT-TEST-1"))
		other = frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": HOLDER,
				"type": "Alert",
				"subject": "Test",
				"document_type": "Sales Invoice",
				"document_name": "SINV-TEST-1",
			}
		).insert(ignore_permissions=True)
		self.assertFalse(other.link)
