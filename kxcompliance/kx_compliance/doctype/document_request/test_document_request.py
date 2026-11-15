# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.api import add_request_document, ask_clients_in_bulk, bulk_ask_plan, documents
from kxcompliance.kx_compliance import document_requests
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
IGNORE_TEST_RECORD_DEPENDENCIES = ["Company", "User", "Sales Invoice"]

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


def emailed(request: str, sender: str, file_name: str = "october-sales.csv"):
	"""A reply to the request's email, as Frappe files it: a Communication and its attachment."""
	reply = frappe.get_doc(
		{
			"doctype": "Communication",
			"communication_type": "Communication",
			"communication_medium": "Email",
			"sent_or_received": "Received",
			"subject": "Re: October sales register",
			"sender": sender,
			"reference_doctype": "Document Request",
			"reference_name": request,
			"content": "Attached.",
		}
	).insert(ignore_permissions=True)
	frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"attached_to_doctype": "Communication",
			"attached_to_name": reply.name,
			"is_private": 1,
			"content": b"invoice,amount\n1,100\n",
		}
	).insert(ignore_permissions=True)


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

	def test_a_client_with_no_login_is_asked_and_reminded_at_its_contact_email(self):
		# A client without a login, but with a contact email the app can write to.
		frappe.db.delete("Compliance Client Login")
		frappe.db.set_value(
			"Compliance Client", "Sunrise Group", "contact_email", "accounts@sunrise.example.com"
		)
		frappe.db.delete("User Permission", {"user": CLIENT_LOGIN, "allow": "Company"})
		with (
			patch(
				"kxcompliance.kx_compliance.document_requests.sender_address",
				return_value="compliance@firm.example.com",
			),
			patch("frappe.sendmail") as sendmail,
		):
			with self.set_user(HOLDER):
				request = ask(compliance_task=self.filing)
			asked_by_email = sendmail.call_args.kwargs
			with self.change_settings(SETTINGS, enabled=1), self.freeze_time("2026-11-08"):
				send_reminders(frappe.utils.getdate("2026-11-08"))
		self.assertEqual(asked_by_email["recipients"], ["accounts@sunrise.example.com"])
		# Filed on the request, so the contact's reply with the file comes back to it.
		self.assertEqual(
			(asked_by_email["reference_doctype"], asked_by_email["reference_name"]),
			("Document Request", request.name),
		)
		self.assertIn("Reply to this email with the file attached", asked_by_email["message"])
		self.assertNotIn("/compliance/requests/", asked_by_email["message"])
		self.assertEqual(sendmail.call_count, 2)
		self.assertEqual(
			frappe.get_all(
				"Compliance Reminder Log", filters={"document_request": request.name}, pluck="sent_to"
			),
			["accounts@sunrise.example.com"],
		)

	def test_asking_every_client_with_a_return_at_once(self):
		profile(SECOND_COMPANY)  # set up, but not linked to a client: cannot be asked
		unlinked = task(SECOND_COMPANY, responsible=HOLDER)
		where = {"obligation_template": "GSTR-3B (Monthly)", "period_end": "2026-10-31"}
		with self.set_user(HOLDER):
			plan = bulk_ask_plan(**where)
			self.assertGreaterEqual(plan["to_ask"], 1)
			self.assertGreaterEqual(plan["no_client"], 1)
			with patch("frappe.enqueue") as enqueue:
				ask_clients_in_bulk(**where, title="October purchase register", details="As Excel")
			job = enqueue.call_args.kwargs
		asking = [row["name"] for row in job["filings"]]
		# The client's filing is asked; the company with no client is not.
		self.assertIn(self.filing, asking)
		self.assertNotIn(unlinked, asking)
		# Whoever asks may have another company as their default; each request is still its filing's.
		frappe.defaults.set_user_default("company", SECOND_COMPANY, HOLDER)
		self.addCleanup(frappe.defaults.clear_user_default, "company", HOLDER)
		# The job, as the worker runs it; it commits as it goes, which a test must not.
		with self.freeze_time("2026-11-01"), patch("frappe.db.commit"):
			document_requests.run_ask_in_bulk(job["filings"], job["title"], job["details"], by=HOLDER)
		frappe.set_user("Administrator")
		made = frappe.get_all(
			"Document Request",
			filters={"compliance_task": self.filing},
			fields=["title", "client", "due_date", "requested_by"],
		)
		self.assertEqual(len(made), 1)
		self.assertEqual(
			(made[0].title, made[0].client, made[0].requested_by),
			("October purchase register", "Sunrise Group", HOLDER),
		)
		self.assertTrue(
			notified(
				CLIENT_LOGIN,
				frappe.get_all("Document Request", filters={"compliance_task": self.filing}, pluck="name")[0],
			)
		)
		self.assertFalse(frappe.db.exists("Document Request", {"compliance_task": unlinked}))
		# Asked once: the same return again skips every filing just asked.
		with self.set_user(HOLDER):
			again = bulk_ask_plan(**where)
		self.assertEqual(again["asked_already"], len(asking))
		self.assertEqual(again["to_ask"], 0)

	def test_a_bulk_request_is_due_before_its_filing(self):
		today = "2026-11-01"
		self.assertEqual(str(document_requests.suggested_due_date("2026-11-20", today)), "2026-11-08")
		self.assertEqual(str(document_requests.suggested_due_date("2026-11-05", today)), "2026-11-04")
		self.assertEqual(str(document_requests.suggested_due_date("2026-11-01", today)), "2026-11-02")

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
		# Frappe adds a suffix when a file of that name is already on disk (as other tests leave).
		self.assertTrue(any(name.startswith("october-sales") and name.endswith(".csv") for name in on_filing))
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

	def test_the_firm_changes_an_open_request_and_the_client_is_told(self):
		from kxcompliance.api import save_changes

		with self.set_user(HOLDER):
			request = ask(compliance_task=self.filing)
		frappe.db.delete(
			"Notification Log", {"document_type": "Document Request", "document_name": request.name}
		)
		with self.set_user(HOLDER):
			save_changes(
				"Document Request",
				request.name,
				{"due_date": "2026-11-14", "title": "October purchase register"},
			)
		request.reload()
		self.assertEqual((str(request.due_date), request.title), ("2026-11-14", "October purchase register"))
		self.assertTrue(notified(CLIENT_LOGIN, request.name))
		# The client's own login reads the request but cannot change it.
		with self.set_user(CLIENT_LOGIN), self.assertRaises(frappe.PermissionError):
			save_changes("Document Request", request.name, {"due_date": "2026-12-01"})

	def test_an_accepted_or_withdrawn_request_is_not_changed(self):
		request = ask(company=TEST_COMPANY)
		request.withdraw()
		request.reload()
		request.due_date = "2026-12-01"
		with self.assertRaisesRegex(
			frappe.ValidationError, "Withdrawn, so its Due Date can no longer be changed"
		):
			request.save()

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

	def test_a_reply_from_the_clients_login_is_taken_as_the_document(self):
		with self.set_user(HOLDER):
			request = ask(compliance_task=self.filing)
		emailed(request.name, f"Client <{frappe.db.get_value('User', CLIENT_LOGIN, 'email')}>")
		request.reload()
		self.assertEqual(request.status, "Uploaded")
		self.assertTrue(
			frappe.db.exists(
				"File",
				{"attached_to_doctype": "Document Request", "attached_to_name": request.name},
			)
		)
		self.assertTrue(notified(HOLDER, request.name))

	def test_a_reply_from_anyone_else_waits_for_a_look(self):
		with self.set_user(HOLDER):
			request = ask(compliance_task=self.filing)
		frappe.db.delete("Notification Log", {"for_user": HOLDER})
		emailed(request.name, "stranger@example.net")
		request.reload()
		self.assertEqual(request.status, "Requested")
		self.assertFalse(
			frappe.db.exists(
				"File",
				{"attached_to_doctype": "Document Request", "attached_to_name": request.name},
			)
		)
		self.assertTrue(notified(HOLDER, request.name))
