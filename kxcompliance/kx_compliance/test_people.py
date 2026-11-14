# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.api import (
	getting_started_checklist,
	hide_getting_started,
	invite_person,
	new_sign_in_link,
	remove_person,
	set_person_role,
	team,
)
from kxcompliance.kx_compliance.test_utils import HOLDER, MANAGER, make_user, make_users

NEWCOMER = "newcomer@example.com"
SETTINGS = "KX Compliance Settings"


class TestPeople(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_users()

	def setUp(self):
		if frappe.db.exists("User", NEWCOMER):
			frappe.delete_doc("User", NEWCOMER, force=True)

	def test_a_manager_invites_someone_who_gets_a_link_when_email_cannot_go(self):
		with self.set_user(MANAGER):
			result = invite_person("Neha Joshi", NEWCOMER, "Staff")
			listed = {person["user"]: person for person in team()}
		self.assertIn("Compliance User", frappe.get_roles(NEWCOMER))
		self.assertEqual(frappe.db.get_value("User", NEWCOMER, "full_name"), "Neha Joshi")
		self.assertEqual(listed[NEWCOMER]["role"], "Staff")
		self.assertTrue(listed[MANAGER]["is_me"])
		if not result["emailed"]:
			self.assertIn("/update-password?key=", result["link"])

	def test_only_managers_change_the_team_and_never_their_own_role(self):
		with self.set_user(HOLDER), self.assertRaises(frappe.PermissionError):
			invite_person("Neha Joshi", NEWCOMER, "Manager")
		with self.set_user(MANAGER):
			with self.assertRaisesRegex(frappe.ValidationError, "your own role"):
				set_person_role(MANAGER, "Staff")
			with self.assertRaisesRegex(frappe.ValidationError, "Manager, Staff or Auditor"):
				invite_person("Neha Joshi", NEWCOMER, "System Manager")
			with self.assertRaisesRegex(frappe.ValidationError, "already on the team"):
				invite_person("Holder", HOLDER, "Staff")

	def test_changing_a_role_and_taking_someone_off_the_team(self):
		with self.set_user(MANAGER):
			invite_person("Neha Joshi", NEWCOMER, "Staff")
			set_person_role(NEWCOMER, "Auditor")
			self.assertEqual(
				set(frappe.get_roles(NEWCOMER)) & {"Compliance User", "Compliance Auditor"},
				{"Compliance Auditor"},
			)
			remove_person(NEWCOMER)
		self.assertFalse(set(frappe.get_roles(NEWCOMER)) & {"Compliance User", "Compliance Auditor"})

	def test_an_administrator_and_someone_signed_in_before_are_left_alone(self):
		admin = make_user("compliance-admin@example.com", ("Compliance Manager", "System Manager"))
		frappe.db.set_value("User", HOLDER, "last_login", "2026-11-01 10:00:00")
		with self.set_user(MANAGER):
			with self.assertRaisesRegex(frappe.ValidationError, "administrator"):
				remove_person(admin)
			with self.assertRaisesRegex(frappe.ValidationError, "signed in before"):
				new_sign_in_link(HOLDER)

	def test_the_checklist_ticks_itself_off_and_can_be_hidden(self):
		with self.change_settings(SETTINGS, enabled=0, email_account=None):
			with self.set_user(MANAGER):
				result = getting_started_checklist()
				steps = {step["key"]: step["done"] for step in result["steps"]}
				self.assertFalse(steps["reminders"])
				self.assertTrue(steps["colleague"])  # the test users are on the team
				self.assertTrue(result["show"])
				hide_getting_started()
				self.assertFalse(getting_started_checklist()["show"])
			with self.set_user(HOLDER):
				self.assertEqual(getting_started_checklist(), {"show": False, "steps": []})
