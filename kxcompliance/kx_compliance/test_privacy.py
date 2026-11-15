# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_to_date, get_datetime, getdate, now_datetime

from kxcompliance.api import (
	accept_privacy_notice,
	boot,
	my_privacy_requests,
	privacy_notice,
	raise_privacy_request,
	save_settings,
	withdraw_privacy_consent,
)
from kxcompliance.kx_compliance import privacy
from kxcompliance.kx_compliance.doctype.signatory.test_signatory import signatory
from kxcompliance.kx_compliance.test_utils import (
	AUDITOR,
	HOLDER,
	MANAGER,
	OTHER_HOLDER,
	make_company,
	make_users,
)

SETTINGS = "KX Compliance Settings"


def breach(**fields):
	return frappe.get_doc(
		{
			"doctype": "Personal Data Breach",
			"title": "Laptop with client files lost",
			"discovered_on": add_to_date(now_datetime(), hours=-5),
			"description": "A staff laptop was stolen from a car.",
			**fields,
		}
	).insert()


class TestPrivacy(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()

	def setUp(self):
		frappe.db.delete("Privacy Consent")
		frappe.db.delete("Privacy Request")
		frappe.db.delete("Personal Data Breach")
		frappe.db.set_single_value(SETTINGS, {"privacy_notice": "", "notice_version": 1})
		frappe.clear_document_cache(SETTINGS, SETTINGS)

	def test_everyone_accepts_the_notice_once_until_it_changes(self):
		with self.set_user(HOLDER):
			self.assertTrue(boot()["privacy_notice_due"])
			notice = privacy_notice()
			self.assertFalse(notice["accepted"])
			self.assertIn("Your rights", notice["text"])
			accept_privacy_notice(notice["version"])
			self.assertFalse(boot()["privacy_notice_due"])
			accept_privacy_notice(notice["version"])
		self.assertEqual(frappe.db.count("Privacy Consent", {"user": HOLDER}), 1)

		settings = frappe.get_doc(SETTINGS)
		settings.privacy_notice = "<p>Our own notice.</p>"
		settings.save()
		self.assertEqual(settings.notice_version, 2)
		with self.set_user(HOLDER):
			self.assertTrue(boot()["privacy_notice_due"])
			self.assertEqual(privacy_notice()["text"], "<p>Our own notice.</p>")
			# Accepting the version read before it changed is refused.
			with self.assertRaisesRegex(frappe.ValidationError, "has changed"):
				accept_privacy_notice(1)
			accept_privacy_notice(2)
			self.assertFalse(boot()["privacy_notice_due"])

	def test_withdrawing_consent_asks_for_it_again(self):
		with self.set_user(HOLDER):
			accept_privacy_notice(1)
			self.assertEqual(withdraw_privacy_consent(), {"withdrawn": 1})
			self.assertTrue(boot()["privacy_notice_due"])
		consent = frappe.get_all("Privacy Consent", filters={"user": HOLDER}, fields=["withdrawn_on"])
		self.assertTrue(consent[0].withdrawn_on)

	def test_a_request_is_due_in_ninety_days_and_seen_only_by_its_requester_and_managers(self):
		with self.set_user(HOLDER):
			made = raise_privacy_request("See my data", "Please send me what you hold about me.")
			self.assertEqual(getdate(made["due_by"]), getdate(add_days(now_datetime(), 90)))
			self.assertEqual([row.name for row in my_privacy_requests()], [made["name"]])
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("Privacy Request", made["name"]).check_permission("read")
		with self.set_user(OTHER_HOLDER):
			self.assertEqual(my_privacy_requests(), [])
		with self.set_user(MANAGER):
			self.assertEqual(len(frappe.get_list("Privacy Request")), 1)
		with self.set_user(HOLDER):
			with self.assertRaisesRegex(frappe.ValidationError, "not a kind"):
				raise_privacy_request("Sell my data", "x")
			with self.assertRaisesRegex(frappe.ValidationError, "Say what"):
				raise_privacy_request("Grievance", "  ")

	def test_closing_a_request_needs_a_response_and_tells_the_person(self):
		with self.set_user(HOLDER):
			name = raise_privacy_request("Correct my data", "My name is spelt wrong.")["name"]
		with self.set_user(MANAGER):
			request = frappe.get_doc("Privacy Request", name)
			request.status = "Done"
			with self.assertRaisesRegex(frappe.ValidationError, "Write the response"):
				request.save()
			request = frappe.get_doc("Privacy Request", name)
			request.status = "Done"
			request.response = "Corrected to Ravi Rao."
			request.save()
			self.assertEqual(request.closed_by, MANAGER)
			self.assertTrue(request.closed_on)
		# Told in the app, as this site sends no email.
		self.assertTrue(
			frappe.db.exists(
				"Notification Log",
				{"for_user": HOLDER, "document_type": "Privacy Request", "document_name": name},
			)
		)

	def test_a_breach_is_due_at_the_board_in_72_hours_and_tracked_until_reported(self):
		with self.set_user(MANAGER):
			doc = breach()
			self.assertEqual(
				get_datetime(doc.board_due_by), add_to_date(get_datetime(doc.discovered_on), hours=72)
			)
			self.assertEqual(doc.status, "Board not told")
			doc.board_reported_on = now_datetime()
			doc.save()
			self.assertEqual(doc.status, "People not told")
			doc.people_informed_on = now_datetime()
			doc.save()
			self.assertEqual(doc.status, "Reported")
			with self.assertRaisesRegex(frappe.ValidationError, "before the breach"):
				breach(board_reported_on=add_to_date(now_datetime(), hours=-10))
			with self.assertRaisesRegex(frappe.ValidationError, "future"):
				breach(discovered_on=add_to_date(now_datetime(), hours=2))
		with self.set_user(AUDITOR), self.assertRaises(frappe.PermissionError):
			breach()

	def test_pan_and_mobile_are_masked_to_all_but_managers_and_never_overwritten(self):
		name = signatory(pan="ABCDE1234F", mobile="9876543210").name
		with self.set_user(HOLDER):
			# As the app receives it: in a list, and as a record sent to the browser.
			[row] = frappe.get_list("Signatory", filters={"name": name}, fields=["pan", "mobile"])
			self.assertEqual((row.pan, row.mobile), ("XXXXXXXX", "987XXXXXX"))
			doc = frappe.get_doc("Signatory", name)
			doc.apply_fieldlevel_read_permissions()
			self.assertEqual((doc.pan, doc.mobile), ("XXXXXXXX", "987XXXXXX"))
			doc.designation = "Managing Director"
			doc.save()
		with self.set_user(MANAGER):
			doc = frappe.get_doc("Signatory", name)
			self.assertEqual((doc.pan, doc.mobile), ("ABCDE1234F", "9876543210"))
			self.assertEqual(doc.designation, "Managing Director")

	def test_old_reminder_log_addresses_are_erased_and_the_entries_kept(self):
		old = frappe.get_doc(
			{
				"doctype": "Compliance Reminder Log",
				"kind": "Digest",
				"sent_to": HOLDER,
				"sent_on": add_days(now_datetime(), -400),
				"log_key": "privacy-test-old",
			}
		).insert(ignore_permissions=True)
		recent = frappe.get_doc(
			{
				"doctype": "Compliance Reminder Log",
				"kind": "Digest",
				"sent_to": HOLDER,
				"sent_on": add_days(now_datetime(), -10),
				"log_key": "privacy-test-recent",
			}
		).insert(ignore_permissions=True)
		privacy.run_daily()
		self.assertEqual(frappe.db.get_value("Compliance Reminder Log", old.name, "sent_to"), "")
		self.assertEqual(frappe.db.get_value("Compliance Reminder Log", recent.name, "sent_to"), HOLDER)

	def test_the_log_is_kept_at_least_a_year(self):
		with self.set_user(MANAGER):
			with self.assertRaisesRegex(frappe.ValidationError, "between 365"):
				save_settings({"reminder_log_days": 30})
			self.assertEqual(save_settings({"reminder_log_days": 730})["reminder_log_days"], 730)

	def test_only_people_of_the_app_see_the_notice(self):
		with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
			privacy_notice()


class TestLanguage(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_users()

	def test_a_person_chooses_english_or_hindi_for_themselves(self):
		from kxcompliance.api import set_my_language

		with self.set_user(HOLDER):
			set_my_language("hi")
			self.assertEqual(frappe.db.get_value("User", HOLDER, "language"), "hi")
			with self.assertRaisesRegex(frappe.ValidationError, "not available"):
				set_my_language("fr")
		with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
			set_my_language("hi")
