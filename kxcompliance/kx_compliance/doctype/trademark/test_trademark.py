# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.kx_compliance.move_old_trackers import move_trademarks
from kxcompliance.kx_compliance.test_utils import (
	HOLDER,
	MANAGER,
	OTHER_HOLDER,
	REVIEWER,
	TEST_COMPANY,
	make_company,
	make_users,
)

# These tests build their own records; skip ERPNext's generated ones.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Company", "User", "Supplier", "Brand", "Compliance Item"]


def make_trademark(**fields):
	values = {
		"doctype": "Trademark",
		"mark": "SAMPLEMARK",
		"classes": [{"class_number": 9}, {"class_number": 42}],
		"application_number": "6123456",
		"filing_date": "2026-03-10",
		"applicant": TEST_COMPANY,
		"responsible": HOLDER,
		"reviewer": REVIEWER,
	}
	values.update(fields)
	return frappe.get_doc(values).insert()


def dates(trademark: str, kind: str):
	return frappe.get_all(
		"Legal Date",
		filters={"reference_doctype": "Trademark", "reference_name": trademark, "kind": kind},
		pluck="date",
	)


class TestTrademark(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		frappe.defaults.set_global_default("company", TEST_COMPANY)

	def test_a_mark_runs_ten_years_from_filing(self):
		self.assertEqual(str(make_trademark().valid_until), "2036-03-10")

	def test_classes_are_1_to_45_and_listed_once(self):
		with self.assertRaisesRegex(frappe.ValidationError, "between 1 and 45"):
			make_trademark(classes=[{"class_number": 46}])
		with self.assertRaisesRegex(frappe.ValidationError, "listed twice"):
			make_trademark(classes=[{"class_number": 9}, {"class_number": 9}])

	def test_registration_needs_its_number_and_date(self):
		trademark = make_trademark()
		trademark.status = "Registered"
		with self.assertRaisesRegex(frappe.ValidationError, "Registration Number.*Registration Date"):
			trademark.save()

	def test_an_examination_report_starts_a_reply_deadline_that_moves_with_it(self):
		trademark = make_trademark()
		trademark.examination_report_on = "2026-06-01"
		trademark.save()
		self.assertEqual(
			[str(day) for day in dates(trademark.name, "Examination Report Reply")], ["2026-07-01"]
		)
		trademark.examination_report_on = "2026-06-05"
		trademark.save()
		self.assertEqual(
			[str(day) for day in dates(trademark.name, "Examination Report Reply")], ["2026-07-05"]
		)
		self.assertEqual(str(frappe.db.get_value("Trademark", trademark.name, "next_date")), "2026-07-05")

	def test_reassigning_a_mark_moves_its_open_dates(self):
		trademark = make_trademark(examination_report_on="2026-06-01")
		with self.set_user(MANAGER):
			theirs = frappe.get_doc("Trademark", trademark.name)
			theirs.responsible = OTHER_HOLDER
			theirs.save()
		people = frappe.get_all(
			"Legal Date",
			filters={"reference_name": trademark.name, "status": "Scheduled"},
			fields=["responsible", "reviewer"],
		)
		self.assertTrue(people)
		self.assertTrue(all(row.responsible == OTHER_HOLDER for row in people))

	def test_advertisement_and_opposition_start_their_windows(self):
		trademark = make_trademark(journal_date="2026-08-15")
		self.assertEqual([str(day) for day in dates(trademark.name, "Opposition Window")], ["2026-12-15"])
		trademark.opposition_notice_on = "2026-11-01"
		trademark.save()
		self.assertEqual([str(day) for day in dates(trademark.name, "Counter-Statement")], ["2027-01-01"])

	def test_registration_makes_a_renewal_record_that_the_trademark_follows(self):
		trademark = make_trademark()
		trademark.update(
			{"status": "Registered", "registration_number": "6123456", "registration_date": "2027-05-01"}
		)
		trademark.save()
		item = frappe.get_doc("Compliance Item", trademark.renewal_item)
		self.assertEqual(item.item_type, "Trademark Registration")
		self.assertEqual(str(item.valid_until), "2036-03-10")
		self.assertEqual(item.company, TEST_COMPANY)

		item.valid_until = "2046-03-10"
		item.save()
		self.assertEqual(str(frappe.db.get_value("Trademark", trademark.name, "valid_until")), "2046-03-10")
		trademark.reload()
		trademark.save()
		self.assertEqual(str(trademark.valid_until), "2046-03-10")

	def test_a_compliance_user_sees_only_their_trademarks(self):
		mine = make_trademark().name
		theirs = make_trademark(responsible=OTHER_HOLDER, reviewer=MANAGER).name
		with self.set_user(HOLDER):
			visible = set(frappe.get_list("Trademark", pluck="name"))
		self.assertIn(mine, visible)
		self.assertNotIn(theirs, visible)

	def test_trademark_tracker_rows_move_to_trademarks(self):
		row = frappe.get_doc(
			{
				"doctype": "Trademark Tracker",
				"document_name": "OLDMARK",
				"issue_date": "2016-02-01",
				"expiry_date": "2026-02-01",
				"status": "Registered",
				"class": "Class 9 and 35",
				"application_number": "3200001",
				"vendor": "Sample IP Agents",
				"activity": "File renewal",
				"activity_deadline": "2030-01-15",
			}
		).insert(ignore_permissions=True)
		move_trademarks()
		self.assertEqual(move_trademarks()["moved"], 0)
		trademark = frappe.get_doc(
			"Trademark", {"source_doctype": "Trademark Tracker", "source_name": row.name}
		)
		self.assertEqual(trademark.status, "Registered")
		self.assertEqual([entry.class_number for entry in trademark.classes], [9, 35])
		self.assertIn("Sample IP Agents", trademark.notes)
		self.assertEqual(
			str(frappe.db.get_value("Compliance Item", trademark.renewal_item, "valid_until")), "2026-02-01"
		)
		self.assertEqual([str(day) for day in dates(trademark.name, "Other")], ["2030-01-15"])

	def test_moving_a_mark_on_records_what_the_registry_sent_and_its_deadline(self):
		mark = make_trademark()
		with self.set_user(HOLDER):
			frappe.get_doc("Trademark", mark.name).change_status(
				"Objected", {"examination_report_on": "2026-11-02"}
			)
		self.assertEqual(frappe.db.get_value("Trademark", mark.name, "status"), "Objected")
		self.assertEqual([str(day) for day in dates(mark.name, "Examination Report Reply")], ["2026-12-02"])
		with self.assertRaisesRegex(frappe.ValidationError, "cannot be set when marking"):
			frappe.get_doc("Trademark", mark.name).change_status("Refused", {"registration_number": "1"})

	def test_registering_needs_its_number_and_date(self):
		mark = make_trademark()
		with self.assertRaisesRegex(frappe.ValidationError, "before marking"):
			frappe.get_doc("Trademark", mark.name).change_status("Registered", {})
		frappe.get_doc("Trademark", mark.name).change_status(
			"Registered", {"registration_number": "R-77", "registration_date": "2026-11-01"}
		)
		self.assertTrue(frappe.db.get_value("Trademark", mark.name, "renewal_item"))

	def test_an_ended_mark_has_nothing_left_scheduled(self):
		mark = make_trademark(examination_report_on="2026-11-02")
		self.assertTrue(dates(mark.name, "Examination Report Reply"))
		frappe.get_doc("Trademark", mark.name).change_status("Abandoned")
		self.assertFalse(
			frappe.db.exists(
				"Legal Date",
				{"reference_doctype": "Trademark", "reference_name": mark.name, "status": "Scheduled"},
			)
		)

	def test_only_its_holder_reviewer_or_a_manager_moves_a_mark(self):
		mark = make_trademark()
		with self.set_user(OTHER_HOLDER), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Trademark", mark.name).change_status("Objected")

	def test_a_trademark_is_added_with_its_classes_held_by_whoever_adds_it(self):
		from kxcompliance.api import add_trademark

		mark = {
			"mark": "NEWMARK",
			"mark_type": "Word",
			"application_number": "7000001",
			"filing_date": "2026-10-01",
			"applicant": TEST_COMPANY,
		}
		with self.set_user(HOLDER):
			name = add_trademark(mark, [{"class_number": 29, "goods_or_services": "Edible oils"}])["name"]
		saved = frappe.get_doc("Trademark", name)
		self.assertEqual((saved.responsible, saved.status), (HOLDER, "New Application"))
		self.assertEqual(
			[(row.class_number, row.goods_or_services) for row in saved.classes], [(29, "Edible oils")]
		)
		with self.assertRaisesRegex(frappe.ValidationError, "class is a number"):
			add_trademark(mark, [{"class_number": 9, "status": "Registered"}])
		with self.assertRaisesRegex(frappe.PermissionError, "cannot set status"):
			add_trademark({**mark, "status": "Registered"}, [{"class_number": 9}])
