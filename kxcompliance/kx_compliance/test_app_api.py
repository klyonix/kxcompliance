# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import json
from urllib.parse import unquote, urlsplit

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.api import (
	app_companies,
	boot,
	editable_fields,
	full_names,
	licence_rule_options,
	log_notice,
	my_work,
	overview,
	save_changes,
	search,
)
from kxcompliance.kx_compliance.overview import desk_link, total
from kxcompliance.kx_compliance.test_utils import (
	AUDITOR,
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
from kxcompliance.www import compliance_manifest

OUTSIDER = "compliance-outsider@example.com"


class TestAppApi(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		make_user(OUTSIDER, ("Accounts User",))
		make_item_type("Test App Licence", grace=10, reminders=(30,))

	def test_my_work_lists_only_what_the_person_holds_or_reviews(self):
		mine = make_item("Test App Licence", days=10, responsible=HOLDER).name
		reviewing = make_item("Test App Licence", days=12, responsible=OTHER_HOLDER, reviewer=HOLDER).name
		theirs = make_item("Test App Licence", days=11, responsible=OTHER_HOLDER, reviewer=MANAGER).name
		with self.set_user(HOLDER):
			names = {item.name for item in my_work()["items"]}
		self.assertTrue({mine, reviewing} <= names)
		self.assertNotIn(theirs, names)

	def test_my_work_needs_a_compliance_role(self):
		with self.set_user(OUTSIDER), self.assertRaises(frappe.PermissionError):
			my_work()

	def test_save_changes_saves_allowed_fields_on_the_persons_own_record(self):
		item = make_item("Test App Licence", responsible=HOLDER)
		with self.set_user(HOLDER):
			result = save_changes(
				"Compliance Item", item.name, {"reference_number": "TL/2026/77"}, str(item.modified)
			)
		self.assertEqual(frappe.db.get_value("Compliance Item", item.name, "reference_number"), "TL/2026/77")
		self.assertTrue(result["modified"])

	def test_save_changes_refuses_fields_and_records_outside_the_app(self):
		item = make_item("Test App Licence", responsible=HOLDER)
		with self.set_user(HOLDER):
			with self.assertRaisesRegex(frappe.PermissionError, "valid_until"):
				save_changes("Compliance Item", item.name, {"valid_until": "2099-01-01"})
			with self.assertRaisesRegex(frappe.PermissionError, "cannot change"):
				save_changes("Compliance Obligation Template", "GSTR-1 (Monthly)", {"due_day": 1})

	def test_save_changes_refuses_another_persons_record(self):
		theirs = make_item("Test App Licence", responsible=OTHER_HOLDER, reviewer=MANAGER)
		with self.set_user(HOLDER), self.assertRaises(frappe.PermissionError):
			save_changes("Compliance Item", theirs.name, {"notes": "mine now"})

	def test_save_changes_corrects_the_details_of_an_item_and_a_case(self):
		item = make_item("Test App Licence", responsible=HOLDER)
		with self.set_user(HOLDER):
			save_changes(
				"Compliance Item", item.name, {"title": "Trade Licence, Pune", "issue_date": "2026-01-05"}
			)
			case = log_notice(
				"Show cause notice", "Tax Notice or Assessment", "Tax Officer", TEST_COMPANY, "2026-12-05"
			)["name"]
			save_changes(
				"Legal Case", case, {"case_number": "ST/42/2026", "opposing_party": "GST Department"}
			)
		self.assertEqual(
			frappe.db.get_value("Compliance Item", item.name, ["title", "issue_date"], as_dict=True),
			{"title": "Trade Licence, Pune", "issue_date": frappe.utils.getdate("2026-01-05")},
		)
		self.assertEqual(frappe.db.get_value("Legal Case", case, "case_number"), "ST/42/2026")

	def test_only_a_manager_changes_who_is_responsible(self):
		item = make_item("Test App Licence", responsible=HOLDER)
		with self.set_user(HOLDER), self.assertRaisesRegex(frappe.PermissionError, "Compliance Manager"):
			save_changes("Compliance Item", item.name, {"responsible": OTHER_HOLDER})
		with self.set_user(MANAGER):
			save_changes("Compliance Item", item.name, {"responsible": OTHER_HOLDER, "reviewer": REVIEWER})
		self.assertEqual(
			frappe.db.get_value("Compliance Item", item.name, ["responsible", "reviewer"]),
			(OTHER_HOLDER, REVIEWER),
		)

	def test_the_app_is_told_what_it_may_change_and_the_choices(self):
		with self.set_user(HOLDER):
			fields = editable_fields("Legal Case")
			with self.assertRaises(frappe.PermissionError):
				editable_fields("Compliance Obligation Template")
		self.assertEqual(fields["fields"]["our_role"]["fieldtype"], "Select")
		self.assertIn("Noticee", fields["fields"]["our_role"]["options"])
		self.assertNotIn("status", fields["fields"])
		# Only a manager is offered the people to reassign to.
		self.assertEqual(fields["people"], [])
		with self.set_user(MANAGER):
			self.assertTrue(editable_fields("Legal Case")["people"])

	def test_save_changes_refuses_a_change_made_on_an_older_copy(self):
		item = make_item("Test App Licence", responsible=HOLDER)
		stale = str(item.modified)
		item.notes = "Changed by someone else"
		item.save()
		with self.set_user(HOLDER), self.assertRaises(frappe.TimestampMismatchError):
			save_changes("Compliance Item", item.name, {"notes": "Offline note"}, stale)

	def test_a_new_notice_is_held_by_its_receiver_with_its_reply_date(self):
		with self.set_user(HOLDER):
			name = log_notice(
				"Show cause notice, GST FY 2024-25",
				"Tax Notice or Assessment",
				"Tax Officer",
				TEST_COMPANY,
				"2026-12-05",
				notice_reference="ZD291126001",
			)["name"]
		case = frappe.get_doc("Legal Case", name)
		self.assertEqual((case.responsible, case.our_role, case.status), (HOLDER, "Noticee", "Open"))
		reply = frappe.get_all(
			"Legal Date",
			filters={"reference_name": name},
			fields=["kind", "date", "responsible", "status"],
		)
		self.assertEqual(len(reply), 1)
		self.assertEqual((reply[0].kind, str(reply[0].date)), ("Reply Due", "2026-12-05"))
		self.assertEqual(reply[0].responsible, HOLDER)
		self.assertEqual(str(case.next_date), "2026-12-05")

	def test_logging_a_notice_needs_a_role_that_may_create_cases(self):
		with self.set_user(AUDITOR), self.assertRaises(frappe.PermissionError):
			log_notice("Notice", "Other", "Other", TEST_COMPANY, "2026-12-05")

	def test_the_app_offers_only_the_companies_a_person_is_permitted(self):
		frappe.db.delete("User Permission", {"user": HOLDER})
		with self.set_user(HOLDER):
			self.assertIn(TEST_COMPANY, app_companies())
		frappe.get_doc(
			{"doctype": "User Permission", "user": HOLDER, "allow": "Company", "for_value": TEST_COMPANY}
		).insert()
		with self.set_user(HOLDER):
			self.assertEqual(app_companies(), [TEST_COMPANY])

	def overview_card(self, section: str, label: str) -> dict:
		with self.set_user(MANAGER):
			result = overview()
		cards = next(group["cards"] for group in result["sections"] if group["title"] == section)
		return next(card for card in cards if card["label"] == label)

	def test_the_overview_counts_what_needs_a_look_and_is_for_managers(self):
		before = self.overview_card("Register", "Expired or lapsed")["value"]
		make_item("Test App Licence", days=-30, responsible=HOLDER)
		after = self.overview_card("Register", "Expired or lapsed")
		self.assertEqual(after["value"], before + 1)
		self.assertTrue(after["link"].startswith("/app/compliance-item?"))
		with self.set_user(HOLDER), self.assertRaises(frappe.PermissionError):
			overview()

	def test_the_licence_rule_screen_offers_documents_by_party_for_managers(self):
		with self.set_user(MANAGER):
			options = licence_rule_options()
		by_doctype = {row["doctype"]: row for row in options["documents"]}
		self.assertEqual(by_doctype["Sales Invoice"]["party_type"], "Customer")
		self.assertEqual(by_doctype["Purchase Order"]["field"], "check_purchase_order")
		self.assertIn("All Item Groups", options["item_groups"])
		with self.set_user(HOLDER), self.assertRaises(frappe.PermissionError):
			licence_rule_options()

	def test_an_overview_number_carries_its_list_filters(self):
		card = self.overview_card("Register", "Expired or lapsed")
		self.assertEqual(card["doctype"], "Compliance Item")
		self.assertIn(["status", "in", ["Expired", "Lapsed"]], card["filters"])
		self.assertIn(["is_overdue", "=", 1], self.overview_card("Filings", "Overdue")["filters"])

	def test_the_overview_marks_what_needs_someone_to_act(self):
		self.assertTrue(self.overview_card("Filings", "Overdue")["act"])
		self.assertTrue(self.overview_card("Filings", "Waiting for review")["act"])
		self.assertFalse(self.overview_card("Register", "Active")["act"])
		self.assertFalse(self.overview_card("Filings", "Filed late")["act"])

	def test_overview_links_carry_their_filters_for_the_desk_list(self):
		link = desk_link(
			"Compliance Item", {"status": ("in", ["Expired", "Lapsed"]), "holder_type": "Company"}
		)
		self.assertEqual(
			link,
			"/app/compliance-item?status=%5B%22in%22%2C+%5B%22Expired%22%2C+%22Lapsed%22%5D%5D"
			"&holder_type=Company",
		)
		rows = [
			frappe._dict(status="Filed", count=6),
			frappe._dict(status="Filed Late", count=2),
			frappe._dict(status="Open", count=1),
		]
		self.assertEqual(total(rows, status=["Filed", "Filed Late"]), 8)
		self.assertEqual(total(rows, status="Open"), 1)

	def test_the_on_time_rate_links_to_its_report(self):
		with self.set_user(MANAGER):
			link = overview()["on_time"]["link"]
		path = unquote(urlsplit(link).path)
		self.assertTrue(path.startswith("/app/query-report/"))
		self.assertTrue(frappe.db.exists("Report", path.removeprefix("/app/query-report/")))

	def test_the_app_shows_people_by_name(self):
		with self.set_user(HOLDER):
			names = full_names(f"{HOLDER},{REVIEWER},,{HOLDER}")
			self.assertEqual(set(names), {HOLDER, REVIEWER})
			self.assertNotIn("@", names[HOLDER])
			with self.assertRaises(frappe.ValidationError):
				full_names(",".join(f"user{number}@example.com" for number in range(60)))
		with self.set_user(OUTSIDER), self.assertRaises(frappe.PermissionError):
			full_names(HOLDER)

	def test_the_app_is_told_the_sites_date_format(self):
		with self.set_user(HOLDER):
			self.assertEqual(boot()["date_format"], frappe.db.get_default("date_format") or "dd-mm-yyyy")

	def test_search_finds_by_number_within_what_the_person_may_see(self):
		mine = make_item("Test App Licence", responsible=HOLDER, reference_number="TL/2026/4471").name
		theirs = make_item(
			"Test App Licence", responsible=OTHER_HOLDER, reviewer=MANAGER, reference_number="TL/2026/4472"
		).name
		with self.set_user(HOLDER):
			found = [row.name for row in search("TL/2026/447")["items"]]
			self.assertIn(mine, found)
			self.assertNotIn(theirs, found)
			self.assertEqual(search(" T ")["items"], [])
			# Staff search the records they work on; the team is a manager's to search.
			kinds = set(search("TL/2026"))
			self.assertTrue({"items", "filings", "cases", "trademarks", "signatories"} <= kinds)
			self.assertNotIn("people", kinds)
		with self.set_user(MANAGER):
			self.assertIn(theirs, [row.name for row in search("4472")["items"]])
		with self.set_user(OUTSIDER), self.assertRaises(frappe.PermissionError):
			search("TL/2026")

	def test_search_matches_every_word_in_any_order_closest_first(self):
		exact = make_item("Test App Licence", title="Fire NOC", reference_number="FN/77").name
		longer = make_item("Test App Licence", title="Fire NOC Pune Warehouse").name
		elsewhere = make_item(
			"Test App Licence", title="Warehouse permit", reference_number="NOC-FIRE-9"
		).name
		with self.set_user(MANAGER):
			found = [row.name for row in search("noc fire")["items"]]
			self.assertEqual(found[:2], [exact, longer])
			self.assertIn(elsewhere, found)
			self.assertEqual([row.name for row in search("pune fire")["items"]], [longer])
			# % and _ are looked for as typed, not as wildcards.
			self.assertEqual(search("fire %")["items"], [])

	def test_save_changes_takes_plain_values_and_people_on_the_team(self):
		item = make_item("Test App Licence", responsible=HOLDER)
		with self.set_user(MANAGER):
			with self.assertRaisesRegex(frappe.ValidationError, "single value"):
				save_changes("Compliance Item", item.name, {"title": ["!=", ""]})
			with self.assertRaisesRegex(frappe.ValidationError, "not on the team"):
				save_changes("Compliance Item", item.name, {"reviewer": "Guest"})
			# The reviewer may be cleared.
			save_changes("Compliance Item", item.name, {"reviewer": None})

	def test_search_puts_an_exact_name_first_however_many_newer_match(self):
		exact = make_item("Test App Licence", title="Fire NOC").name
		for index in range(35):
			make_item("Test App Licence", title=f"Fire NOC renewal {index}")
		with self.set_user(MANAGER):
			self.assertEqual(search("fire noc", kind="items")["items"][0].name, exact)

	def test_search_one_kind_and_the_team_for_managers_only(self):
		with self.set_user(MANAGER):
			only_items = search("Test", kind="items")
			self.assertEqual(set(only_items), {"items"})
			self.assertIn(
				HOLDER, [person["user"] for person in search("compliance", kind="people")["people"]]
			)
		with self.set_user(HOLDER):
			self.assertNotIn("people", search("compliance"))

	def test_the_manifest_carries_the_sites_name_and_logo(self):
		with self.change_settings(
			"KX Compliance Settings", app_name="Acme Compliance", app_logo="/files/acme.png"
		):
			manifest = json.loads(compliance_manifest.get_context(frappe._dict())["manifest"])
		self.assertEqual(manifest["name"], "Acme Compliance")
		self.assertEqual(manifest["start_url"], "/compliance")
		self.assertEqual(manifest["icons"][0]["src"], "/files/acme.png")

	def test_the_app_logo_must_be_public(self):
		settings = frappe.get_doc("KX Compliance Settings")
		settings.app_logo = "/private/files/logo.png"
		with self.assertRaisesRegex(frappe.ValidationError, "public file"):
			settings.save()
