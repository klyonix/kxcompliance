# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

from io import BytesIO

import frappe
from frappe.model import get_permitted_fields
from frappe.tests import IntegrationTestCase
from werkzeug.test import EnvironBuilder

from kxcompliance.api import (
	add_client_document,
	app_companies,
	client_choices,
	client_detail,
	client_of_login,
	clients_overview,
	documents,
	search,
)
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

SECOND_COMPANY = "Client Test Second Company"
CLIENT_LOGIN = "asha@sunrise-client.example.com"
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


def with_login(name: str = "Sunrise Group", enabled: int = 1):
	return client(name, logins=[{"full_name": "Asha Rao", "email": CLIENT_LOGIN, "enabled": enabled}])


def uploading(file_name: str, content: bytes = b"date,amount\n2026-10-01,1200\n"):
	"""A request carrying one file, as the app's upload sends it."""
	return EnvironBuilder(method="POST", data={"file": (BytesIO(content), file_name)}).get_request()


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
		frappe.db.delete("Compliance Client Login")
		frappe.db.delete("Compliance Client")
		frappe.db.delete(
			"User Permission",
			{"user": ("in", [HOLDER, OTHER_HOLDER, MANAGER, CLIENT_LOGIN]), "allow": "Company"},
		)
		frappe.db.delete("Compliance Task", {"task_key": ("like", "client-test|%")})
		# Those deletes skip Frappe's caches of each person's permissions; a request starts afresh.
		for user in (HOLDER, OTHER_HOLDER, MANAGER, CLIENT_LOGIN):
			frappe.cache.hdel("user_permissions", user)
		frappe.local.request_cache.clear()

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

	def test_a_client_login_searches_only_what_it_can_open(self):
		sunrise = with_login()
		profile(TEST_COMPANY, sunrise.name)
		task(TEST_COMPANY)
		with self.set_user(CLIENT_LOGIN):
			found = search("GSTR")
			self.assertTrue(found["filings"])
			# The client, its company profile, licence rules and obligations are pages it cannot open.
			for kind in ("clients", "companies", "rules", "obligations", "people", "customers"):
				self.assertNotIn(kind, found)
			self.assertEqual(search("GSTR", kind="obligations"), {})

	def test_staff_on_one_team_still_see_the_work_they_hold_elsewhere(self):
		sunrise = client("Sunrise Group", team=(HOLDER,))
		profile(TEST_COMPANY, sunrise.name)
		company(OTHER_COMPANY, "CTOC")
		moonrise = client("Moonrise Retail", team=(OTHER_HOLDER,))
		profile(OTHER_COMPANY, moonrise.name)
		theirs_but_mine = task(OTHER_COMPANY, responsible=HOLDER)
		only_theirs = task(OTHER_COMPANY, responsible=OTHER_HOLDER)
		with self.set_user(HOLDER):
			seen = frappe.get_list("Compliance Task", pluck="name")
			self.assertIn(theirs_but_mine, seen)
			self.assertTrue(frappe.has_permission("Compliance Task", "read", doc=theirs_but_mine))
			# Not on that client's team: the rest of its work stays out of sight.
			self.assertNotIn(only_theirs, seen)

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

	def test_a_login_reads_its_clients_companies_without_the_firms_remarks(self):
		sunrise = with_login()
		profile(TEST_COMPANY, sunrise.name)
		profile(OTHER_COMPANY)
		theirs = task(TEST_COMPANY)
		frappe.db.set_value("Compliance Task", theirs, "remarks", "Client is slow to send papers")
		outside = task(OTHER_COMPANY)
		user = frappe.get_doc("User", CLIENT_LOGIN)
		self.assertEqual((user.user_type, user.enabled), ("Website User", 1))
		self.assertIn("Compliance Client", frappe.get_roles(CLIENT_LOGIN))
		self.assertEqual(company_permissions(CLIENT_LOGIN), {TEST_COMPANY})
		with self.set_user(CLIENT_LOGIN):
			self.assertEqual(set(frappe.get_list("Compliance Task", pluck="name")), {theirs})
			self.assertNotIn(outside, frappe.get_list("Compliance Task", pluck="name"))
			self.assertFalse(frappe.has_permission("Compliance Task", "write", doc=theirs))
			self.assertNotIn("remarks", get_permitted_fields("Compliance Task", user=CLIENT_LOGIN))
			filing = frappe.get_doc("Compliance Task", theirs)
			filing.apply_fieldlevel_read_permissions()
			self.assertIsNone(filing.get("remarks"))
			self.assertEqual(frappe.get_list("Compliance Client", pluck="name"), ["Sunrise Group"])
			self.assertEqual(client_of_login(), "Sunrise Group")
			self.assertEqual(app_companies(), [TEST_COMPANY])
			self.assertEqual(client_detail("Sunrise Group")["logins"], ["Asha Rao"])
			with self.assertRaises(frappe.PermissionError):
				clients_overview()

	def test_turning_a_login_off_disables_the_user_and_removes_access(self):
		sunrise = with_login()
		profile(TEST_COMPANY, sunrise.name)
		sunrise.reload()
		sunrise.logins[0].enabled = 0
		sunrise.save()
		self.assertEqual(frappe.db.get_value("User", CLIENT_LOGIN, "enabled"), 0)
		self.assertEqual(company_permissions(CLIENT_LOGIN), set())
		sunrise.logins[0].enabled = 1
		sunrise.save()
		self.assertEqual(frappe.db.get_value("User", CLIENT_LOGIN, "enabled"), 1)
		self.assertEqual(company_permissions(CLIENT_LOGIN), {TEST_COMPANY})
		sunrise.status = "Left"
		sunrise.save()
		self.assertEqual(frappe.db.get_value("User", CLIENT_LOGIN, "enabled"), 0)
		sunrise.status = "Active"
		sunrise.save()
		sunrise.logins = []
		sunrise.save()
		self.assertEqual(frappe.db.get_value("User", CLIENT_LOGIN, "enabled"), 0)
		self.assertEqual(company_permissions(CLIENT_LOGIN), set())

	def test_a_firm_user_cannot_be_a_client_login(self):
		with self.assertRaises(frappe.ValidationError):
			client(logins=[{"full_name": "Firm person", "email": HOLDER}])
		with self.assertRaises(frappe.ValidationError):
			client(
				logins=[
					{"full_name": "Asha Rao", "email": CLIENT_LOGIN},
					{"full_name": "Asha again", "email": CLIENT_LOGIN.upper()},
				]
			)

	def test_a_login_uploads_a_document_and_the_responsible_person_is_told(self):
		sunrise = with_login()
		profile(TEST_COMPANY, sunrise.name)
		profile(OTHER_COMPANY)
		theirs = task(TEST_COMPANY, responsible=HOLDER)
		outside = task(OTHER_COMPANY)
		request = frappe.local.request if hasattr(frappe.local, "request") else None
		try:
			with self.set_user(CLIENT_LOGIN):
				frappe.local.request = uploading("october-sales.csv")
				added = add_client_document(theirs)
				frappe.local.request = uploading("october-sales.csv")
				with self.assertRaises(frappe.PermissionError):
					add_client_document(outside)
				frappe.local.request = uploading("run-me.sh", b"echo hi")
				with self.assertRaises(frappe.ValidationError):
					add_client_document(theirs)
			with self.set_user(HOLDER):
				frappe.local.request = uploading("october-sales.csv")
				with self.assertRaises(frappe.PermissionError):
					add_client_document(theirs)
		finally:
			frappe.local.request = request
		document = frappe.get_doc("File", added["name"])
		self.assertEqual(
			(document.attached_to_doctype, document.attached_to_name, document.is_private),
			("Compliance Task", theirs, 1),
		)
		self.assertTrue(
			frappe.db.exists(
				"Notification Log",
				{"for_user": HOLDER, "document_type": "Compliance Task", "document_name": theirs},
			)
		)
		with self.set_user(CLIENT_LOGIN):
			self.assertTrue(frappe.has_permission("File", "read", doc=document))
			self.assertEqual([row.name for row in documents("Compliance Task", theirs)], [document.name])
			with self.assertRaises(frappe.PermissionError):
				documents("Compliance Task", outside)
			with self.assertRaises(frappe.PermissionError):
				documents("User", CLIENT_LOGIN)

	def test_the_team_and_the_clients_logins_see_its_hearings_and_deadlines(self):
		from kxcompliance.kx_compliance.doctype.legal_case.test_legal_case import make_case, make_date

		sunrise = with_login()  # with HOLDER on its team
		profile(TEST_COMPANY, sunrise.name)
		profile(OTHER_COMPANY)
		ours = make_case(company=TEST_COMPANY, responsible=MANAGER, reviewer=None)
		theirs = make_case(company=OTHER_COMPANY, responsible=MANAGER, reviewer=None)
		our_date = make_date(ours.name, "2026-12-01").name
		make_date(theirs.name, "2026-12-02")
		self.assertEqual(frappe.db.get_value("Legal Date", our_date, "company"), TEST_COMPANY)
		for user in (HOLDER, CLIENT_LOGIN):
			with self.set_user(user):
				self.assertEqual(frappe.get_list("Legal Date", pluck="name"), [our_date])
		# The date follows its case to another company.
		ours.company = OTHER_COMPANY
		ours.save()
		self.assertEqual(frappe.db.get_value("Legal Date", our_date, "company"), OTHER_COMPANY)

	def test_the_lists_offer_the_clients_a_person_works_on(self):
		sunrise = client("Sunrise Group")
		client("Moonlight Traders", team=(OTHER_HOLDER,))
		gone = client("Old Client", status="Left")
		profile(TEST_COMPANY, sunrise.name)
		profile(SECOND_COMPANY, sunrise.name)
		profile(OTHER_COMPANY, gone.name)
		with self.set_user(HOLDER):
			self.assertEqual(
				client_choices(),
				[{"name": "Sunrise Group", "companies": sorted([TEST_COMPANY, SECOND_COMPANY])}],
			)
		with self.set_user(MANAGER):
			self.assertEqual(
				[row["name"] for row in client_choices()], ["Moonlight Traders", "Sunrise Group"]
			)
		with self.set_user(CLIENT_LOGIN), self.assertRaises(frappe.PermissionError):
			client_choices()

	def test_the_firms_people_are_offered_to_its_staff(self):
		with_login()
		from kxcompliance.api import people_options

		with self.set_user(MANAGER):
			people = {row.name for row in people_options()}
		self.assertTrue({HOLDER, OTHER_HOLDER, MANAGER} <= people)
		self.assertNotIn(CLIENT_LOGIN, people)
		# Anyone who records items picks a reviewer; a client's login picks nobody.
		with self.set_user(HOLDER):
			self.assertIn(MANAGER, {row.name for row in people_options()})
		with self.set_user(CLIENT_LOGIN), self.assertRaises(frappe.PermissionError):
			people_options()


class TestRelationshipManagerEscalation(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		company(SECOND_COMPANY, "CTSC")
		company(OTHER_COMPANY, "CTOC")

	def test_an_overdue_filing_also_goes_to_the_clients_relationship_manager(self):
		from unittest.mock import patch

		from kxcompliance.kx_compliance.reminders import relationship_managers
		from kxcompliance.kx_compliance.statutory import send_task_escalations

		client("Sunrise Group", relationship_manager=OTHER_HOLDER)
		profile(SECOND_COMPANY, "Sunrise Group")
		left = client("Moonlight Traders", relationship_manager=HOLDER, status="Left")
		profile(OTHER_COMPANY, left.name)
		self.assertEqual(
			relationship_managers([SECOND_COMPANY, OTHER_COMPANY, TEST_COMPANY, None]),
			{SECOND_COMPANY: OTHER_HOLDER},
		)
		overdue = task(SECOND_COMPANY)
		with patch("kxcompliance.kx_compliance.statutory.notify") as notify:
			send_task_escalations(frappe.utils.getdate("2026-12-31"))
		sent = {call.args[4]: call.args[0] for call in notify.call_args_list}
		self.assertIn(OTHER_HOLDER, sent[overdue])
		self.assertIn(MANAGER, sent[overdue])
