# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.tests import IntegrationTestCase

from compliance_plus.api import app_companies, boot, full_names, log_notice, my_work, overview, save_changes
from compliance_plus.compliance_plus.overview import desk_link, total
from compliance_plus.compliance_plus.test_utils import (
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
from compliance_plus.www import compliance_manifest

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

	def test_the_manifest_carries_the_sites_name_and_logo(self):
		with self.change_settings(
			"Compliance Plus Settings", app_name="Acme Compliance", app_logo="/files/acme.png"
		):
			manifest = json.loads(compliance_manifest.get_context(frappe._dict())["manifest"])
		self.assertEqual(manifest["name"], "Acme Compliance")
		self.assertEqual(manifest["start_url"], "/compliance")
		self.assertEqual(manifest["icons"][0]["src"], "/files/acme.png")

	def test_the_app_logo_must_be_public(self):
		settings = frappe.get_doc("Compliance Plus Settings")
		settings.app_logo = "/private/files/logo.png"
		with self.assertRaisesRegex(frappe.ValidationError, "public file"):
			settings.save()
