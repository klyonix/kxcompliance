# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from kxcompliance.api import erase_privacy_requester, my_personal_data, privacy_request_data
from kxcompliance.kx_compliance import personal_data, privacy
from kxcompliance.kx_compliance.doctype.signatory.test_signatory import signatory
from kxcompliance.kx_compliance.test_bulk_filing import filing
from kxcompliance.kx_compliance.test_utils import MANAGER, OTHER_HOLDER, make_company, make_user, make_users

LEAVER = "leaving-person@example.com"


def privacy_request(user: str, request_type: str) -> str:
	frappe.set_user(user)
	name = privacy.raise_request(request_type, "Please act on my data.")["name"]
	frappe.set_user("Administrator")
	return name


class TestPersonalData(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_users()
		make_company()

	def setUp(self):
		make_user(LEAVER, ("Compliance User",))
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_a_person_sees_what_the_app_holds_about_them(self):
		filing("GSTR-3B (Monthly)", "2026-10-31", "2026-11-20", responsible=LEAVER)
		signatory("Leaving Person", email=LEAVER, pan="ABCDE1234F", din="01234567", mobile="9876543210")

		with self.set_user(LEAVER):
			data = my_personal_data()

		self.assertEqual(data["person"]["email"], LEAVER)
		self.assertIn("Compliance User", data["person"]["roles"])
		self.assertIn("Filings", {row["label"] for row in data["records"]})
		self.assertEqual(data["signatory"][0]["pan"], "ABCDE1234F")
		self.assertEqual(data["signatory"][0]["din"], "01234567")

	def test_a_manager_sees_it_for_a_see_my_data_request_and_staff_cannot(self):
		request = privacy_request(LEAVER, "See my data")
		with self.set_user(MANAGER):
			self.assertEqual(privacy_request_data(request)["person"]["email"], LEAVER)
		with self.set_user(OTHER_HOLDER), self.assertRaises(frappe.PermissionError):
			privacy_request_data(request)
		grievance = privacy_request(LEAVER, "Grievance")
		with self.set_user(MANAGER), self.assertRaises(frappe.ValidationError):
			privacy_request_data(grievance)

	def test_erasing_is_checked_before_it_starts(self):
		request = privacy_request(LEAVER, "Erase my data")
		with self.set_user(MANAGER):
			self.assertRaises(
				frappe.ValidationError, erase_privacy_requester, request, OTHER_HOLDER, "someone@else.com"
			)
			self.assertRaises(frappe.ValidationError, erase_privacy_requester, request, LEAVER, LEAVER)
			self.assertRaises(
				frappe.ValidationError, erase_privacy_requester, request, "nobody@example.com", LEAVER
			)
		with self.set_user(OTHER_HOLDER), self.assertRaises(frappe.PermissionError):
			erase_privacy_requester(request, MANAGER, LEAVER)
		own = privacy_request(MANAGER, "Erase my data")
		with self.set_user(MANAGER), self.assertRaises(frappe.ValidationError):
			erase_privacy_requester(own, OTHER_HOLDER, MANAGER)

	def test_erasing_hands_over_the_work_and_keeps_the_records_without_the_person(self):
		task = filing("GSTR-3B (Monthly)", "2026-10-31", "2026-11-20", responsible=LEAVER)
		person = signatory(
			"Leaving Person", email=LEAVER, pan="ABCDE1234F", din="07654321", mobile="9876543210"
		)
		request = privacy_request(LEAVER, "Erase my data")
		consent = frappe.get_doc(
			{
				"doctype": "Privacy Consent",
				"user": LEAVER,
				"notice_version": 1,
				"accepted_on": frappe.utils.now(),
			}
		).insert(ignore_permissions=True)

		with self.set_user(MANAGER):
			erase_privacy_requester(request, OTHER_HOLDER, LEAVER)
		self.assertEqual(frappe.db.get_value("Privacy Request", request, "status"), "In Progress")
		# The job commits as it goes; here the test's own transaction stays open.
		with patch("frappe.db.commit"):
			personal_data.erase(request, OTHER_HOLDER, MANAGER)
		frappe.set_user("Administrator")

		self.assertEqual(frappe.db.get_value("Compliance Task", task, "responsible"), OTHER_HOLDER)
		self.assertFalse(frappe.db.exists("User", LEAVER))
		erased = frappe.db.get_value("Privacy Consent", consent.name, "user")
		self.assertTrue(erased.endswith("@erased.invalid"))
		login = frappe.db.get_value(
			"User", erased, ["enabled", "first_name", "mobile_no", "email"], as_dict=True
		)
		self.assertEqual((login.enabled, login.mobile_no, login.email), (0, None, erased))
		self.assertTrue(login.first_name.startswith("Erased person"))

		kept = frappe.db.get_value(
			"Signatory",
			person.name,
			["full_name", "din", "pan", "email", "mobile", "is_active"],
			as_dict=True,
		)
		self.assertEqual((kept.full_name, kept.din, kept.is_active), ("Leaving Person", "07654321", 0))
		self.assertFalse(kept.pan or kept.email or kept.mobile)
		done = frappe.get_doc("Privacy Request", request)
		self.assertEqual(done.status, "Done")
		self.assertTrue(done.erased_on)
		self.assertEqual(done.requested_by, erased)
		self.assertTrue(done.requester_name.startswith("Erased person"))
		self.assertIn("erased", done.response)
		# No copy of their email is left in change history, nor their login's own history.
		self.assertFalse(frappe.db.count("Version", {"data": ("like", f"%{LEAVER}%")}))
		self.assertFalse(
			frappe.db.count("Version", {"ref_doctype": "User", "docname": ("in", [LEAVER, erased])})
		)
		self.assertFalse(frappe.db.count("Comment", {"comment_email": LEAVER}))

	def test_requests_are_aimed_at_30_days_and_never_past_90(self):
		request = frappe.get_doc("Privacy Request", privacy_request(LEAVER, "Grievance"))
		self.assertEqual(getdate(request.due_by), getdate(add_days(nowdate(), 30)))
		self.assertEqual(getdate(request.latest_by), getdate(add_days(nowdate(), 90)))

	def test_reminders_come_before_on_and_weekly_after_the_target_urgent_near_the_limit(self):
		due, latest = "2026-12-01", "2027-01-01"
		expected = {
			"2026-11-24": "soon",
			"2026-11-25": None,
			"2026-12-01": "due",
			"2026-12-05": None,
			"2026-12-08": "late",
			"2026-12-15": "late",
			"2026-12-22": "urgent",
			"2026-12-23": None,
			"2027-01-01": "urgent",
			"2027-01-05": "urgent",
		}
		for today, kind in expected.items():
			with self.subTest(today=today):
				self.assertEqual(privacy.reminder_due(due, latest, today), kind)

	def test_managers_hear_of_a_request_on_its_day(self):
		request = privacy_request(LEAVER, "Grievance")
		due_by = frappe.db.get_value("Privacy Request", request, "due_by")
		with patch(
			"frappe.desk.doctype.notification_log.notification_log.enqueue_create_notification"
		) as tell:
			privacy.remind_about_requests(due_by)
		told = [call.args for call in tell.call_args_list if call.args[1]["document_name"] == request]
		self.assertTrue(told)
		self.assertIn(MANAGER, told[0][0])
		self.assertNotIn(LEAVER, told[0][0])
		self.assertIn("due today", told[0][1]["subject"])

	def test_the_patch_gives_older_requests_their_dates(self):
		from kxcompliance.patches.v1_0.set_privacy_answer_dates import execute

		request = privacy_request(LEAVER, "Grievance")
		received = frappe.db.get_value("Privacy Request", request, "received_on")
		table = frappe.qb.DocType("Privacy Request")
		frappe.qb.update(table).set(table.latest_by, None).set(
			table.due_by, add_days(getdate(received), 90)
		).where(table.name == request).run()

		execute()
		execute()

		dates = frappe.db.get_value("Privacy Request", request, ["due_by", "latest_by"], as_dict=True)
		self.assertEqual(getdate(dates.due_by), getdate(add_days(getdate(received), 30)))
		self.assertEqual(getdate(dates.latest_by), getdate(add_days(getdate(received), 90)))
