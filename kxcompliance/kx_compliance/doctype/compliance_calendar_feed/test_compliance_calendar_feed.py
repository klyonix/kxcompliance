# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

from datetime import UTC, datetime

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.kx_compliance.calendar_feed import (
	events_for,
	feed,
	feed_settings,
	set_up_feed,
	stop_feed,
)
from kxcompliance.kx_compliance.doctype.compliance_client.test_compliance_client import (
	CLIENT_LOGIN,
	OTHER_COMPANY,
	client,
	company,
	profile,
	task,
	with_login,
)
from kxcompliance.kx_compliance.ical import calendar, escape, fold
from kxcompliance.kx_compliance.test_utils import (
	HOLDER,
	MANAGER,
	OTHER_HOLDER,
	TEST_COMPANY,
	make_company,
	make_users,
)

# These tests build their own records; skip ERPNext's generated ones.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Company", "User"]


def token_of(url: str) -> str:
	return url.split("token=", 1)[1]


def fetch(token: str) -> str:
	with IntegrationTestCase.set_user("Guest"):
		feed(token)
	return frappe.response.filecontent


class TestCalendarFeed(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		company(OTHER_COMPANY, "CTOC")

	def setUp(self):
		frappe.db.delete("Compliance Calendar Feed")
		frappe.db.delete("Compliance Task", {"task_key": ("like", "client-test|%")})
		frappe.db.delete("Compliance Client Login")
		frappe.db.delete("Compliance Client Access")
		frappe.db.delete("Compliance Client Member")
		frappe.db.delete("Compliance Client")
		for name in (TEST_COMPANY, OTHER_COMPANY):
			if frappe.db.exists("Company Compliance Profile", name):
				frappe.delete_doc("Company Compliance Profile", name, force=True)
		frappe.db.delete("User Permission", {"user": ("in", [HOLDER, CLIENT_LOGIN]), "allow": "Company"})
		self.mine = task(TEST_COMPANY, responsible=HOLDER)
		self.theirs = task(TEST_COMPANY, responsible=OTHER_HOLDER)

	def test_the_feed_writes_valid_icalendar(self):
		text = calendar(
			"Rao, Associates",
			[
				{"uid": "a@site", "start": datetime(2026, 11, 20).date(), "summary": "GSTR-3B; Nov"},
				{
					"uid": "b@site",
					"start": datetime(2026, 11, 21, 10, 30),
					"summary": "Hearing " + "x" * 100,
				},
			],
			"Asia/Kolkata",
			now=datetime(2026, 11, 14, tzinfo=UTC),
		)
		self.assertTrue(text.startswith("BEGIN:VCALENDAR\r\n") and text.endswith("END:VCALENDAR\r\n"))
		self.assertIn("X-WR-CALNAME:Rao\\, Associates", text)
		self.assertIn("DTSTART;VALUE=DATE:20261120\r\nDTEND;VALUE=DATE:20261121", text)
		self.assertIn("SUMMARY:GSTR-3B\\; Nov", text)
		# 10:30 in India is 05:00 UTC.
		self.assertIn("DTSTART:20261121T050000Z\r\nDTEND:20261121T060000Z", text)
		self.assertTrue(all(len(line.encode()) <= 75 for line in text.split("\r\n")))
		self.assertEqual(escape("a\nb\\c"), "a\\nb\\\\c")
		self.assertEqual(fold("x" * 80).split("\r\n "), ["x" * 75, "x" * 5])

	def test_a_person_gets_a_secret_link_to_their_own_work(self):
		with self.set_user(HOLDER):
			self.assertEqual(feed_settings()["url"], "")
			url = set_up_feed()["url"]
			self.assertEqual(feed_settings()["url"], url)
		text = fetch(token_of(url))
		self.assertIn(self.mine, text)
		self.assertNotIn(self.theirs, text)
		self.assertEqual(frappe.session.user, "Administrator")
		self.assertNotIn(token_of(url), frappe.db.get_value("Compliance Calendar Feed", HOLDER, "token_hash"))

	def test_a_new_link_stops_the_old_one_and_stopping_ends_it(self):
		with self.set_user(HOLDER):
			old = token_of(set_up_feed()["url"])
			new = token_of(set_up_feed(new_link=True)["url"])
		self.assertNotEqual(old, new)
		with self.assertRaises(frappe.PermissionError):
			fetch(old)
		fetch(new)
		with self.set_user(HOLDER):
			stop_feed()
		with self.assertRaises(frappe.PermissionError):
			fetch(new)
		with self.assertRaises(frappe.PermissionError):
			fetch("too-short")

	def test_only_managers_show_everything(self):
		with self.set_user(HOLDER), self.assertRaises(frappe.PermissionError):
			set_up_feed("Everything I Can See")
		with self.set_user(MANAGER):
			url = set_up_feed("Everything I Can See")["url"]
		text = fetch(token_of(url))
		self.assertIn(self.mine, text)
		self.assertIn(self.theirs, text)

	def test_a_clients_login_sees_its_filings(self):
		sunrise = with_login()
		profile(TEST_COMPANY, sunrise.name)
		moonlight = client("Moonlight Traders").name
		profile(OTHER_COMPANY, moonlight)
		outside = task(OTHER_COMPANY)
		with self.set_user(CLIENT_LOGIN):
			names = {event["uid"].split("@")[0] for event in events_for(CLIENT_LOGIN, "My Work")}
		self.assertIn(f"compliance_task-{self.mine}", names)
		self.assertIn(f"compliance_task-{self.theirs}", names)
		self.assertNotIn(f"compliance_task-{outside}", names)
