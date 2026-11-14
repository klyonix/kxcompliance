# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from compliance_plus.api import client_detail, clients_overview
from compliance_plus.compliance_plus.test_utils import (
	HOLDER,
	MANAGER,
	OTHER_HOLDER,
	TEST_COMPANY,
	make_company,
	make_users,
)

# These tests build their own records; skip ERPNext's generated ones.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Company", "User"]

SECOND_COMPANY = "Client Test Second Company"
OTHER_COMPANY = "Client Test Other Company"


def company(name: str, abbr: str) -> str:
	if not frappe.db.exists("Company", name):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": name,
				"abbr": abbr,
				"default_currency": "INR",
				"country": "India",
			}
		).insert()
	return name


def profile(company_name: str, client: str | None = None):
	if frappe.db.exists("Company Compliance Profile", company_name):
		frappe.delete_doc("Company Compliance Profile", company_name, force=True)
	return frappe.get_doc(
		{
			"doctype": "Company Compliance Profile",
			"company": company_name,
			"company_type": "Private Limited",
			"default_responsible": MANAGER,
			"client": client,
		}
	).insert()


def client(name: str = "Sunrise Group", team=(HOLDER,), **fields):
	if frappe.db.exists("Compliance Client", name):
		frappe.delete_doc("Compliance Client", name, force=True)
	return frappe.get_doc(
		{
			"doctype": "Compliance Client",
			"client_name": name,
			"team": [{"user": user} for user in team],
			**fields,
		}
	).insert()


def task(company_name: str, responsible: str = MANAGER) -> str:
	return (
		frappe.get_doc(
			{
				"doctype": "Compliance Task",
				"obligation_template": "GSTR-3B (Monthly)",
				"company": company_name,
				"period_start": "2026-10-01",
				"period_end": "2026-10-31",
				"period_label": "Oct 2026",
				"due_date": "2026-11-20",
				"status": "Open",
				"responsible": responsible,
				"task_key": f"client-test|{company_name}|{frappe.generate_hash(length=6)}",
			}
		)
		.insert()
		.name
	)


def company_permissions(user: str) -> set[str]:
	return set(
		frappe.get_all("User Permission", filters={"user": user, "allow": "Company"}, pluck="for_value")
	)


class TestComplianceClient(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		company(SECOND_COMPANY, "CTSC")
		company(OTHER_COMPANY, "CTOC")

	def setUp(self):
		# Data stays until the class ends, so clear what an earlier test may have left.
		for name in (TEST_COMPANY, SECOND_COMPANY, OTHER_COMPANY):
			if frappe.db.exists("Company Compliance Profile", name):
				frappe.delete_doc("Company Compliance Profile", name, force=True)
		frappe.db.delete("Compliance Client Access")
		frappe.db.delete("Compliance Client Member")
		frappe.db.delete("Compliance Client")
		frappe.db.delete(
			"User Permission", {"user": ("in", [HOLDER, OTHER_HOLDER, MANAGER]), "allow": "Company"}
		)
		frappe.db.delete("Compliance Task", {"task_key": ("like", "client-test|%")})

	def test_the_team_sees_every_filing_of_the_clients_companies(self):
		sunrise = client()
		profile(TEST_COMPANY, sunrise.name)
		profile(SECOND_COMPANY, sunrise.name)
		profile(OTHER_COMPANY)
		theirs = task(SECOND_COMPANY)
		outside = task(OTHER_COMPANY)
		self.assertEqual(company_permissions(HOLDER), {TEST_COMPANY, SECOND_COMPANY})
		with self.set_user(HOLDER):
			visible = set(frappe.get_list("Compliance Task", pluck="name"))
			self.assertIn(theirs, visible)
			self.assertNotIn(outside, visible)
			self.assertTrue(frappe.has_permission("Compliance Task", "read", doc=theirs))
		with self.set_user(OTHER_HOLDER):
			self.assertNotIn(theirs, set(frappe.get_list("Compliance Task", pluck="name")))

	def test_leaving_the_team_removes_only_what_the_app_made(self):
		frappe.get_doc(
			{"doctype": "User Permission", "user": HOLDER, "allow": "Company", "for_value": SECOND_COMPANY}
		).insert()
		sunrise = client()
		profile(TEST_COMPANY, sunrise.name)
		profile(SECOND_COMPANY, sunrise.name)
		sunrise.reload()
		sunrise.team = []
		sunrise.save()
		self.assertEqual(company_permissions(HOLDER), {SECOND_COMPANY})
		self.assertFalse(frappe.db.exists("Compliance Client Access", {"user": HOLDER}))

	def test_a_client_who_left_is_no_longer_seen_and_managers_are_never_narrowed(self):
		sunrise = client(team=(HOLDER, MANAGER))
		profile(TEST_COMPANY, sunrise.name)
		self.assertEqual(company_permissions(MANAGER), set())
		self.assertEqual(company_permissions(HOLDER), {TEST_COMPANY})
		sunrise.reload()
		sunrise.status = "Left"
		sunrise.save()
		self.assertEqual(company_permissions(HOLDER), set())

	def test_staff_see_only_their_own_clients(self):
		client("Sunrise Group")
		client("Moonlight Traders", team=(OTHER_HOLDER,))
		with self.set_user(HOLDER):
			self.assertEqual(frappe.get_list("Compliance Client", pluck="name"), ["Sunrise Group"])
		with self.set_user(MANAGER):
			self.assertEqual(len(frappe.get_list("Compliance Client", pluck="name")), 2)

	def test_moving_a_company_to_another_client_moves_who_sees_it(self):
		sunrise = client("Sunrise Group")
		moonlight = client("Moonlight Traders", team=(OTHER_HOLDER,))
		second = profile(SECOND_COMPANY, sunrise.name)
		self.assertEqual(company_permissions(HOLDER), {SECOND_COMPANY})
		second.client = moonlight.name
		second.save()
		self.assertEqual(company_permissions(HOLDER), set())
		self.assertEqual(company_permissions(OTHER_HOLDER), {SECOND_COMPANY})

	def test_the_clients_screen_puts_the_worst_client_first(self):
		sunrise = client("Sunrise Group")
		moonlight = client("Moonlight Traders")
		profile(TEST_COMPANY, sunrise.name)
		profile(SECOND_COMPANY, moonlight.name)
		late = task(SECOND_COMPANY)
		frappe.db.set_value("Compliance Task", late, "is_overdue", 1)
		task(TEST_COMPANY)
		with self.set_user(HOLDER), self.freeze_time("2026-11-15"):
			overview = clients_overview()
			self.assertEqual([row.name for row in overview], ["Moonlight Traders", "Sunrise Group"])
			self.assertEqual((overview[0].overdue, overview[0].companies), (1, [SECOND_COMPANY]))
			detail = client_detail("Sunrise Group")
		self.assertEqual([row.company for row in detail["companies"]], [TEST_COMPANY])
		self.assertEqual(len(detail["filings"]), 1)
		self.assertEqual(detail["due_this_week"], 1)
		with self.set_user(OTHER_HOLDER), self.assertRaises(frappe.PermissionError):
			client_detail("Sunrise Group")
