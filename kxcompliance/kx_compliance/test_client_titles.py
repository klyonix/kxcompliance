# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Clients and rate cards named by a hidden ID: people still see their names."""

import frappe

from kxcompliance.kx_compliance import billing, clients, companies
from kxcompliance.kx_compliance.register import client_named, client_title, client_titles, rate_card_title
from kxcompliance.kx_compliance.test_utils import TEST_COMPANY, make_company, named_by_id
from kxcompliance.testing import IntegrationTestCase


class TestClientTitles(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		cls.ids = named_by_id("Compliance Client", "Rate Card")
		cls.ids.__enter__()
		cls.card = frappe.get_doc({"doctype": "Rate Card", "title": "Titled Card"}).insert()
		cls.client = frappe.get_doc(
			{"doctype": "Compliance Client", "client_name": "Titled Group", "rate_card": cls.card.name}
		).insert()
		if frappe.db.exists("Company Compliance Profile", TEST_COMPANY):
			frappe.db.set_value("Company Compliance Profile", TEST_COMPANY, "client", cls.client.name)
		else:
			frappe.get_doc(
				{
					"doctype": "Company Compliance Profile",
					"company": TEST_COMPANY,
					"company_type": "Private Limited",
					"default_responsible": "Administrator",
					"client": cls.client.name,
				}
			).insert()

	@classmethod
	def tearDownClass(cls):
		cls.ids.__exit__(None, None, None)
		super().tearDownClass()

	def test_the_records_are_named_by_id(self):
		self.assertNotEqual(self.client.name, "Titled Group")
		self.assertNotEqual(self.card.name, "Titled Card")

	def test_lookups_go_by_the_name_people_use(self):
		self.assertEqual(client_named("Titled Group"), self.client.name)
		self.assertIsNone(client_named(self.client.name))
		self.assertEqual(client_title(self.client.name), "Titled Group")
		self.assertEqual(client_titles([self.client.name, None]), {self.client.name: "Titled Group"})
		self.assertEqual(rate_card_title(self.card.name), "Titled Card")

	def test_the_screens_are_sent_the_name(self):
		overview = next(row for row in clients.clients_overview() if row.name == self.client.name)
		self.assertEqual(overview.client_name, "Titled Group")
		choice = next(row for row in clients.client_choices() if row["name"] == self.client.name)
		self.assertEqual(choice["client_name"], "Titled Group")
		self.assertEqual(clients.client_detail(self.client.name)["client_name"], "Titled Group")
		listed = next(
			row for row in companies.companies_overview()["companies"] if row.company == TEST_COMPANY
		)
		self.assertEqual(listed.client_name, "Titled Group")
		self.assertEqual(companies.company_detail(TEST_COMPANY)["client_name"], "Titled Group")
		self.assertIn(
			{"name": self.client.name, "client_name": "Titled Group"},
			[
				{"name": row.name, "client_name": row.client_name}
				for row in companies.form_options()["clients"]
			],
		)

	def test_messages_say_the_name(self):
		with self.assertRaises(frappe.ValidationError) as raised:
			billing.payer(self.client.name, "Not One Of Its Companies")
		self.assertIn("Titled Group", str(raised.exception))
		self.assertNotIn(self.client.name, str(raised.exception))
