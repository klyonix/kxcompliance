# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.kx_compliance.clients import HELD
from kxcompliance.kx_compliance.doctype.compliance_client.test_compliance_client import client, profile
from kxcompliance.kx_compliance.test_utils import (
	MANAGER,
	TEST_COMPANY,
	make_company,
	make_user,
	make_users,
)

# These tests build their own records; skip ERPNext's generated ones.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Company", "User"]

ELSEWHERE = "Held Access Test Company"
# People of their own, so no work another test left behind counts as theirs.
HOLDER = "held-access-holder@example.com"
OTHER_HOLDER = "held-access-other@example.com"


def task_at(company: str, responsible: str) -> str:
	return (
		frappe.get_doc(
			{
				"doctype": "Compliance Task",
				"obligation_template": "GSTR-3B (Monthly)",
				"company": company,
				"period_start": "2026-10-01",
				"period_end": "2026-10-31",
				"period_label": "2026-10",
				"due_date": "2026-11-20",
				"status": "Open",
				"responsible": responsible,
				"task_key": f"held-test|{company}|{frappe.generate_hash(length=6)}",
			}
		)
		.insert()
		.name
	)


def sees(user: str, company: str) -> bool:
	return bool(frappe.db.exists("User Permission", {"user": user, "allow": "Company", "for_value": company}))


class TestComplianceHeldAccess(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		make_user(HOLDER, ("Compliance User",))
		make_user(OTHER_HOLDER, ("Compliance User",))
		if not frappe.db.exists("Company", ELSEWHERE):
			frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": ELSEWHERE,
					"abbr": "HATC",
					"default_currency": "INR",
					"country": "India",
				}
			).insert()

	def setUp(self):
		# HOLDER is on one client's team, so kept to its company; the other company is another's.
		profile(TEST_COMPANY)
		profile(ELSEWHERE)
		ours = client("Held Access Our Client", team=(HOLDER,)).name
		profile(TEST_COMPANY, ours)
		theirs = client("Held Access Their Client", team=(MANAGER,)).name
		profile(ELSEWHERE, theirs)
		self.assertTrue(sees(HOLDER, TEST_COMPANY))
		self.assertFalse(sees(HOLDER, ELSEWHERE))

	def test_work_held_at_another_clients_company_shows_it_until_it_is_done(self):
		first = task_at(ELSEWHERE, HOLDER)
		second = task_at(ELSEWHERE, HOLDER)
		self.assertTrue(sees(HOLDER, ELSEWHERE))
		self.assertEqual(frappe.db.count(HELD, {"user": HOLDER, "company": ELSEWHERE}), 1)

		# Still holding the second, they still see the company.
		doc = frappe.get_doc("Compliance Task", first)
		doc.responsible = OTHER_HOLDER
		doc.save()
		self.assertTrue(sees(HOLDER, ELSEWHERE))

		# Holding nothing open there, they no longer do.
		frappe.delete_doc("Compliance Task", second)
		self.assertFalse(sees(HOLDER, ELSEWHERE))
		self.assertFalse(frappe.db.exists(HELD, {"user": HOLDER, "company": ELSEWHERE}))

	def test_the_teams_own_access_is_never_taken_away(self):
		# HOLDER's work at their own client's company gives nothing extra, and finishing it there
		# leaves the team's access alone.
		name = task_at(TEST_COMPANY, HOLDER)
		self.assertFalse(frappe.db.exists(HELD, {"user": HOLDER, "company": TEST_COMPANY}))
		frappe.delete_doc("Compliance Task", name)
		self.assertTrue(sees(HOLDER, TEST_COMPANY))

	def test_off_the_team_but_holding_work_keeps_the_company_until_it_is_done(self):
		name = task_at(TEST_COMPANY, HOLDER)
		# Taken off the client's team while still holding its filing.
		ours = frappe.get_doc("Compliance Client", {"client_name": "Held Access Our Client"})
		ours.team = [row for row in ours.team if row.user != HOLDER]
		ours.append("team", {"user": OTHER_HOLDER})
		ours.save()
		self.assertTrue(sees(HOLDER, TEST_COMPANY))
		self.assertTrue(frappe.db.exists(HELD, {"user": HOLDER, "company": TEST_COMPANY}))
		frappe.delete_doc("Compliance Task", name)
		self.assertFalse(sees(HOLDER, TEST_COMPANY))
