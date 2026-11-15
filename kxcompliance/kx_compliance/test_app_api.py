# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import json
from urllib.parse import unquote, urlsplit

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.api import (
	add_one_off_filing,
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
	search_counts,
)
from kxcompliance.kx_compliance.overview import desk_link, total
from kxcompliance.kx_compliance.test_bulk_filing import filing
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

	def test_my_work_narrows_to_a_clients_companies_before_its_limit(self):
		from unittest.mock import patch

		mine = make_item("Test App Licence", days=10, responsible=HOLDER).name
		make_item("Test App Licence", days=11, responsible=HOLDER)
		with self.set_user(HOLDER):
			self.assertIn(mine, {item.name for item in my_work(json.dumps([TEST_COMPANY]))["items"]})
			self.assertEqual(my_work(json.dumps(["Another client's company"]))["items"], [])
			self.assertFalse(my_work(json.dumps(["Another client's company"]))["limited"])
			with patch("kxcompliance.api.WORK_LIMIT", 1):
				self.assertTrue(my_work()["limited"])

	def test_staff_add_a_one_off_filing_from_the_library_held_by_them(self):
		filing = {
			"obligation_template": "GSTR-3B (Monthly)",
			"company": TEST_COMPANY,
			"period_label": "Revised return, Sep 2026",
			"due_date": "2026-12-05",
		}
		with self.set_user(HOLDER):
			name = add_one_off_filing(filing)["name"]
			with self.assertRaisesRegex(frappe.PermissionError, "Only a Compliance Manager"):
				add_one_off_filing({**filing, "responsible": OTHER_HOLDER})
		saved = frappe.get_doc("Compliance Task", name)
		self.assertEqual(
			(saved.responsible, saved.status, saved.period_label),
			(HOLDER, "Open", "Revised return, Sep 2026"),
		)
		self.assertTrue(saved.task_key.startswith("one-off|"))
		with self.set_user(MANAGER):
			other = add_one_off_filing({**filing, "responsible": OTHER_HOLDER, "reviewer": REVIEWER})["name"]
		self.assertEqual(
			frappe.db.get_value("Compliance Task", other, ["responsible", "reviewer"]),
			(OTHER_HOLDER, REVIEWER),
		)

	def test_a_one_off_filing_needs_a_return_from_the_library_and_its_due_date(self):
		filing = {"company": TEST_COMPANY, "period_label": "Once", "due_date": "2026-12-05"}
		with self.set_user(HOLDER):
			with self.assertRaisesRegex(frappe.ValidationError, "obligation library"):
				add_one_off_filing({**filing, "obligation_template": "Not A Return"})
			with self.assertRaisesRegex(frappe.ValidationError, "due date"):
				add_one_off_filing({**filing, "obligation_template": "GSTR-3B (Monthly)", "due_date": ""})
			with self.assertRaisesRegex(frappe.PermissionError, "cannot set status"):
				add_one_off_filing({**filing, "obligation_template": "GSTR-3B (Monthly)", "status": "Filed"})
		with self.set_user(OUTSIDER), self.assertRaises(frappe.PermissionError):
			add_one_off_filing({**filing, "obligation_template": "GSTR-3B (Monthly)"})

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
		self.assertTrue(after["link"].startswith("/desk/compliance-item?"))
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
			"/desk/compliance-item?status=%5B%22in%22%2C+%5B%22Expired%22%2C+%22Lapsed%22%5D%5D"
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
		self.assertTrue(path.startswith("/desk/query-report/"))
		self.assertTrue(frappe.db.exists("Report", path.removeprefix("/desk/query-report/")))

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

	def test_search_pages_through_every_match_and_counts_them(self):
		exact = make_item("Test App Licence", title="Boiler NOC").name
		for index in range(35):
			make_item("Test App Licence", title=f"Boiler NOC renewal {index}")
		with self.set_user(MANAGER):
			total = search_counts("boiler noc")["items"]
			first = search("boiler noc", kind="items", start=0, page_length=20)["items"]
			second = search("boiler noc", kind="items", start=20, page_length=20)["items"]
			self.assertEqual(search("boiler noc", kind="items", page_length=1000)["items"].__len__(), 36)
		self.assertEqual(total, 36)
		self.assertEqual(first[0].name, exact)
		self.assertEqual((len(first), len(second)), (20, 16))
		# Each page carries on from the last: no record twice, none left out.
		self.assertEqual(len({row.name for row in first + second}), 36)

	def test_staff_cannot_reassign_by_saving_the_record_itself(self):
		item = make_item("Test App Licence", responsible=HOLDER)
		with self.set_user(HOLDER):
			mine = frappe.get_doc("Compliance Item", item.name)
			mine.notes = "Kept in the office file"
			mine.save()  # anything else of their own they may change
			# Still holding it, they cannot pick its reviewer either: that is a manager's choice.
			mine.reviewer = OTHER_HOLDER
			with self.assertRaisesRegex(frappe.PermissionError, "Reviewer .* from nobody to"):
				mine.save()

	def test_a_manager_reassigns_a_filing_and_staff_cannot(self):
		task = filing("GSTR-3B (Monthly)", "2026-10-31", "2026-11-20", responsible=HOLDER)
		with self.set_user(HOLDER), self.assertRaisesRegex(frappe.PermissionError, "Compliance Manager"):
			save_changes("Compliance Task", task, {"responsible": OTHER_HOLDER})
		with self.set_user(MANAGER):
			save_changes("Compliance Task", task, {"responsible": OTHER_HOLDER, "reviewer": REVIEWER})
		self.assertEqual(
			frappe.db.get_value("Compliance Task", task, ["responsible", "reviewer"]),
			(OTHER_HOLDER, REVIEWER),
		)

	def test_the_overview_narrows_to_one_clients_companies(self):
		make_item("Test App Licence", responsible=HOLDER)
		register = lambda result: next(s for s in result["sections"] if s["key"] == "register")  # noqa: E731
		active = lambda result: sum(card["value"] for card in register(result)["cards"])  # noqa: E731
		with self.set_user(MANAGER):
			everyone = overview()
			theirs = overview(companies=f'["{TEST_COMPANY}"]')
			nobody = overview(companies='["A company that is not here"]')
			with self.assertRaises(frappe.ValidationError):
				overview(companies='{"name": ["!=", ""]}')
		self.assertGreater(active(everyone), 0)
		self.assertEqual(active(theirs), active(everyone))
		self.assertEqual(active(nobody), 0)
		self.assertEqual(nobody["scores"], [])

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
