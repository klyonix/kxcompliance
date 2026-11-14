# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.api import add_request_document, documents
from kxcompliance.kx_compliance.doctype.compliance_client.test_compliance_client import (
	CLIENT_LOGIN,
	OTHER_COMPANY,
	SECOND_COMPANY,
	client,
	company,
	profile,
	task,
	uploading,
	with_login,
)
from kxcompliance.kx_compliance.document_requests import refresh_overdue, reminder_due, send_reminders
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

SETTINGS = "KX Compliance Settings"


def ask(title: str = "October sales register", **fields):
	return frappe.get_doc(
		{
			"doctype": "Document Request",
			"title": title,
			"due_date": "2026-11-10",
			"details": "As an Excel file, one row per invoice.",
			**fields,
		}
	).insert()


def notified(user: str, request: str) -> bool:
	return bool(
		frappe.db.exists(
			"Notification Log",
			{"for_user": user, "document_type": "Document Request", "document_name": request},
		)
	)


def upload_as(user: str, request: str, file_name: str = "october-sales.csv"):
	previous = getattr(frappe.local, "request", None)
	try:
		with IntegrationTestCase.set_user(user):
			frappe.local.request = uploading(file_name)
			return add_request_document(request)
	finally:
		frappe.local.request = previous


class TestDocumentRequest(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		company(SECOND_COMPANY, "CTSC")
		company(OTHER_COMPANY, "CTOC")

	def setUp(self):
		frappe.db.delete("Document Request")
		frappe.db.delete("Compliance Reminder Log", {"kind": "Document Request"})
		for name in (TEST_COMPANY, SECOND_COMPANY, OTHER_COMPANY):
			if frappe.db.exists("Company Compliance Profile", name):
				frappe.delete_doc("Company Compliance Profile", name, force=True)
		frappe.db.delete("Compliance Client Access")
		frappe.db.delete("Compliance Client Member")
		frappe.db.delete("Compliance Client Login")
		frappe.db.delete("Compliance Client")
		frappe.db.delete(
			"User Permission",
			{"user": ("in", [HOLDER, OTHER_HOLDER, MANAGER, CLIENT_LOGIN]), "allow": "Company"},
		)
		sunrise = with_login()
		profile(TEST_COMPANY, sunrise.name)
		self.filing = task(TEST_COMPANY, responsible=HOLDER)

	def test_asking_from_a_filing_tells_the_clients_logins(self):
		with self.set_user(HOLDER):
			request = ask(compliance_task=self.filing)
		self.assertEqual(
			(request.company, request.client, request.requested_by, request.status),
			(TEST_COMPANY, "Sunrise Group", HOLDER, "Requested"),
		)
		self.assertTrue(notified(CLIENT_LOGIN, request.name))
		profile(OTHER_COMPANY)
		with self.assertRaises(frappe.ValidationError):
			ask(company=OTHER_COMPANY)

	def test_the_client_uploads_and_the_firm_accepts_or_sends_it_back(self):
		with self.set_user(HOLDER):
			request = ask(compliance_task=self.filing)
		upload_as(CLIENT_LOGIN, request.name)
		request.reload()
		self.assertEqual(request.status, "Uploaded")
		self.assertTrue(notified(HOLDER, request.name))
		on_filing = frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Compliance Task", "attached_to_name": self.filing},
			pluck="file_name",
		)
		self.assertIn("october-sales.csv", on_filing)
		with self.set_user(CLIENT_LOGIN):
			self.assertEqual(len(documents("Document Request", request.name)), 1)
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("Document Request", request.name).accept()

		with self.set_user(HOLDER):
			request = frappe.get_doc("Document Request", request.name)
			with self.assertRaises(frappe.ValidationError):
				request.send_back("")
			request.send_back("This is September; we need October.")
		self.assertEqual((request.status, request.firm_note[:7]), ("Requested", "This is"))

		upload_as(CLIENT_LOGIN, request.name, "october-sales-v2.csv")
		with self.set_user(HOLDER):
			request = frappe.get_doc("Document Request", request.name)
			request.accept()
		self.assertEqual((request.status, request.accepted_by), ("Accepted", HOLDER))
		with self.assertRaises(frappe.ValidationError):
			upload_as(CLIENT_LOGIN, request.name)

	def test_status_moves_only_through_its_actions(self):
		request = ask(company=TEST_COMPANY)
		request.status = "Accepted"
		with self.assertRaises(frappe.ValidationError):
			request.save()
		request.reload()
		with self.assertRaises(frappe.ValidationError):
			request.accept()  # nothing uploaded yet
		request.withdraw()
		self.assertEqual(request.status, "Withdrawn")

	def test_people_see_only_requests_of_their_clients(self):
		moonlight = client("Moonlight Traders", team=(OTHER_HOLDER,))
		profile(SECOND_COMPANY, moonlight.name)
		ours = ask(company=TEST_COMPANY).name
		theirs = ask(company=SECOND_COMPANY).name
		with self.set_user(CLIENT_LOGIN):
			self.assertEqual(frappe.get_list("Document Request", pluck="name"), [ours])
			with self.assertRaises(frappe.PermissionError):
				upload_as(CLIENT_LOGIN, theirs)
		with self.set_user(OTHER_HOLDER):
			self.assertEqual(frappe.get_list("Document Request", pluck="name"), [theirs])
		with self.set_user(HOLDER):
			self.assertEqual(frappe.get_list("Document Request", pluck="name"), [ours])

	def test_reminders_two_days_before_on_the_day_then_weekly(self):
		self.assertEqual([days for days in range(5, -16, -1) if reminder_due(days)], [2, 0, -7, -14])
		with self.set_user(HOLDER):
			request = ask(due_date="2026-11-10")

		def logs() -> list:
			return frappe.get_all(
				"Compliance Reminder Log",
				filters={"document_request": request.name},
				fields=["rule_days", "sent_to"],
				order_by="creation asc",
			)

		with self.change_settings(SETTINGS, enabled=1):
			for day in ("2026-11-07", "2026-11-08", "2026-11-08", "2026-11-10", "2026-11-11", "2026-11-17"):
				with self.freeze_time(day):
					refresh_overdue(frappe.utils.getdate(day))
					send_reminders(frappe.utils.getdate(day))
		# The client on the two days before, on the day and a week late; the requester once, the day
		# after it fell due. Running a day twice sends nothing more.
		self.assertEqual(
			[(row.rule_days, row.sent_to) for row in logs()],
			[(2, CLIENT_LOGIN), (0, CLIENT_LOGIN), (0, HOLDER), (-7, CLIENT_LOGIN)],
		)
		self.assertEqual(frappe.db.get_value("Document Request", request.name, "is_overdue"), 1)
