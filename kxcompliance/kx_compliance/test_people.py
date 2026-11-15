# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.api import (
	former_people,
	getting_started_checklist,
	hand_over_work,
	hide_getting_started,
	invite_person,
	new_sign_in_link,
	person,
	remove_person,
	send_password_reset,
	set_person_role,
	set_temporary_password,
	team,
)
from kxcompliance.kx_compliance import handover
from kxcompliance.kx_compliance.test_bulk_filing import filing
from kxcompliance.kx_compliance.test_utils import (
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

	def test_a_persons_page_shows_their_role_and_the_work_they_hold(self):
		make_company()
		make_item_type("Test People Licence")
		make_item("Test People Licence", responsible=HOLDER)
		with self.set_user(MANAGER):
			holder = person(HOLDER)
			with self.assertRaises(frappe.DoesNotExistError):
				person("Administrator")
		self.assertEqual(holder["role"], "Staff")
		work = {card["doctype"]: card for card in holder["work"]}
		self.assertGreaterEqual(work["Compliance Item"]["value"], 1)
		self.assertEqual(work["Compliance Item"]["filters"][0], ["responsible", "=", HOLDER])
		self.assertEqual(set(work), {"Compliance Task", "Compliance Item", "Legal Case", "Trademark"})
		with self.set_user(HOLDER), self.assertRaises(frappe.PermissionError):
			person(MANAGER)

	def test_a_manager_sets_a_temporary_password_that_signs_the_person_out(self):
		with self.set_user(MANAGER):
			invite_person("Neha Joshi", NEWCOMER, "Staff")
			with self.assertRaisesRegex(frappe.ValidationError, "at least 8"):
				set_temporary_password(NEWCOMER, "short")
			set_temporary_password(NEWCOMER, "Kx!Temporary-2026-pass")
			with self.assertRaisesRegex(frappe.ValidationError, "your own role"):
				set_temporary_password(MANAGER, "Kx!Temporary-2026-pass")
		frappe.local.login_manager = None
		self.assertEqual(frappe.utils.password.check_password(NEWCOMER, "Kx!Temporary-2026-pass"), NEWCOMER)
		self.assertTrue(
			frappe.db.exists(
				"Comment",
				{"reference_doctype": "User", "reference_name": NEWCOMER, "comment_type": "Info"},
			)
		)
		with self.set_user(HOLDER), self.assertRaises(frappe.PermissionError):
			set_temporary_password(NEWCOMER, "Kx!Another-2026-pass")

	def test_a_reset_link_is_emailed_only_where_email_can_go(self):
		with self.set_user(MANAGER):
			invite_person("Neha Joshi", NEWCOMER, "Staff")
			if frappe.db.exists("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}):
				self.assertTrue(send_password_reset(NEWCOMER)["emailed"])
			else:
				with self.assertRaisesRegex(frappe.ValidationError, "cannot send email"):
					send_password_reset(NEWCOMER)

	def test_a_manager_hands_someones_open_work_to_another(self):
		make_company()
		make_item_type("Test People Licence")
		item = make_item("Test People Licence", responsible=HOLDER, reviewer=REVIEWER).name
		task = filing("GSTR-3B (Monthly)", "2026-10-31", "2026-11-20", responsible=OTHER_HOLDER)
		frappe.db.set_value("Compliance Task", task, "reviewer", HOLDER)
		done = filing("GSTR-1 (Monthly)", "2026-10-31", "2026-11-11", responsible=HOLDER, status="Filed")
		with self.set_user(MANAGER):
			counts = {kind["label"]: kind["count"] for kind in person(HOLDER)["handover"]}
			self.assertGreaterEqual(counts["Register items"], 1)
			self.assertGreaterEqual(counts["Filings"], 1)
			with self.assertRaisesRegex(frappe.ValidationError, "not on the team"):
				hand_over_work(HOLDER, "Guest")
			with patch("frappe.enqueue") as enqueue:
				hand_over_work(HOLDER, OTHER_HOLDER)
			self.assertEqual(enqueue.call_args.kwargs["to_user"], OTHER_HOLDER)
		# The job itself, as the worker runs it; it commits as it goes, which a test must not.
		with patch("frappe.db.commit"):
			handover.run(HOLDER, OTHER_HOLDER, by=MANAGER)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Compliance Item", item, "responsible"), OTHER_HOLDER)
		# They were the reviewer of a filing the new person holds: it has no reviewer now.
		self.assertEqual(
			frappe.db.get_value("Compliance Task", task, ["responsible", "reviewer"]), (OTHER_HOLDER, None)
		)
		# Work already done stays with whoever did it.
		self.assertEqual(frappe.db.get_value("Compliance Task", done, "responsible"), HOLDER)

	def test_someone_off_the_team_with_work_is_listed_to_hand_over(self):
		make_company()
		make_item_type("Test People Licence")
		with self.set_user(MANAGER):
			invite_person("Neha Joshi", NEWCOMER, "Staff")
		make_item("Test People Licence", responsible=NEWCOMER)
		with self.set_user(MANAGER):
			remove_person(NEWCOMER)
			self.assertIn(NEWCOMER, [row["user"] for row in former_people()])
			page = person(NEWCOMER)
		self.assertFalse(page["on_team"])
		self.assertIsNone(page["role"])

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
