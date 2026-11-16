# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.kx_compliance.setup_import import check_rows, read_sheet, template
from kxcompliance.kx_compliance.test_utils import (
	HOLDER,
	MANAGER,
	REVIEWER,
	TEST_COMPANY,
	make_company,
	make_users,
	named_by_id,
)

# These tests build their own records; skip ERPNext's generated ones.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Company", "User"]

NEW_COMPANY = "Bulk Setup Test Foods Private Limited"
# Made by the hidden-ID test, so the other tests still find NEW_COMPANY new.
ID_COMPANY = "Bulk Setup Hidden Id Private Limited"
HEADINGS = "client,company,company kind,responsible,reviewer,team,gstin,tan,pt,pt state"


def sheet(*rows: str) -> bytes:
	return "\n".join([HEADINGS, *rows]).encode()


def row(company: str = NEW_COMPANY, client: str = "Bulk Test Group", **values) -> str:
	cells = {
		"company kind": "Private Limited",
		"responsible": HOLDER,
		"reviewer": REVIEWER,
		"team": HOLDER,
		"gstin": '"29AAKCS1234F1Z5, 27AAKCS1234F1Z7"',
		"tan": "BLRS12345A",
		"pt": "",
		"pt state": "",
		**values,
	}
	return ",".join([client, company, *(cells[key] for key in HEADINGS.split(",")[2:])])


def checked(*rows: str, account_type: str = "CA/CS Firm") -> list[dict]:
	return check_rows(read_sheet(sheet(*rows), "companies.csv"), account_type)


class TestComplianceSetupImport(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()

	def setUp(self):
		frappe.db.delete("Compliance Setup Import")
		for company_name in (NEW_COMPANY, TEST_COMPANY):
			if frappe.db.exists("Company Compliance Profile", company_name):
				frappe.delete_doc("Company Compliance Profile", company_name, force=True)
		# By the name people use: a client may be named by a hidden ID (see named_by_id).
		frappe.db.delete(
			"Compliance Client", {"client_name": ("in", ["Bulk Test Group", "Bulk Other Group"])}
		)

	def test_the_template_reads_back_as_its_example(self):
		rows = read_sheet(template(), "template.xlsx")
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["company"], "Sunrise Foods Private Limited")
		with self.assertRaises(frappe.ValidationError):
			read_sheet(b"x", "companies.pdf")
		with self.assertRaises(frappe.ValidationError):
			read_sheet(b"name,amount\nA,1", "companies.csv")

	def test_a_good_row_reads_its_gst_states_and_says_what_it_will_make(self):
		[result] = checked(row())
		self.assertEqual(result["outcome"], "Ready", result.get("message"))
		self.assertEqual(result["message"], "New client · new company · Private Limited · GST (2), TAN")
		gst = [reg for reg in result["values"]["registrations"] if reg["registration_type"] == "GST"]
		self.assertEqual([reg["state"] for reg in gst], ["Karnataka", "Maharashtra"])

	def test_each_problem_is_named_on_its_row(self):
		results = checked(
			row(client=""),
			row(company="Bulk Second", **{"company kind": "Trust"}),
			row(company="Bulk Third", responsible="nobody@example.com"),
			row(company="Bulk Fourth", gstin="29AAKCS1234F1Z"),
			row(company="Bulk Fifth", pt="PTKA1"),
			row(),
		)
		self.assertEqual([result["outcome"] for result in results], ["Error"] * 5 + ["Ready"])
		self.assertIn("client", results[0]["message"])
		self.assertIn("Company Kind", results[1]["message"])
		self.assertIn("nobody@example.com", results[2]["message"])
		self.assertIn("29AAKCS1234F1Z", results[3]["message"])
		self.assertIn("PT State", results[4]["message"])
		# An organisation needs no client.
		self.assertEqual(checked(row(client=""), account_type="Organisation")[0]["outcome"], "Ready")

	def test_a_company_set_up_already_is_skipped_and_a_repeat_is_an_error(self):
		frappe.get_doc(
			{
				"doctype": "Company Compliance Profile",
				"company": TEST_COMPANY,
				"company_type": "Private Limited",
				"default_responsible": MANAGER,
			}
		).insert()
		results = checked(row(TEST_COMPANY), row(), row())
		self.assertEqual([result["outcome"] for result in results], ["Skipped", "Ready", "Error"])
		self.assertIn("row 3", results[2]["message"])

	def test_importing_sets_up_the_client_company_and_filings(self):
		setup = frappe.get_doc({"doctype": "Compliance Setup Import"}).insert()
		frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "companies.csv",
				"attached_to_doctype": setup.doctype,
				"attached_to_name": setup.name,
				"is_private": 1,
				"content": sheet(row(), row(TEST_COMPANY, gstin="")),
			}
		).insert()
		setup.check_sheet()
		self.assertEqual((setup.status, setup.total_rows, setup.failed), ("Checked", 2, 0))
		with patch("frappe.enqueue") as enqueue:
			setup.start_import()
		self.assertEqual(enqueue.call_args.kwargs["doc_method"], "run_import")
		# The job commits as it goes; a test must not.
		with patch.object(frappe.db, "commit"):
			setup.run_import()
		self.assertEqual((setup.status, setup.made), ("Done", 2))
		profile = frappe.get_doc("Company Compliance Profile", NEW_COMPANY)
		self.assertEqual(
			(
				frappe.db.get_value("Compliance Client", profile.client, "client_name"),
				profile.default_responsible,
			),
			("Bulk Test Group", HOLDER),
		)
		self.assertEqual(len(profile.registrations), 3)
		client = frappe.get_doc("Compliance Client", profile.client)
		self.assertEqual([member.user for member in client.team], [HOLDER])
		self.assertTrue(frappe.db.exists("Compliance Task", {"company": NEW_COMPANY}))
		with self.assertRaises(frappe.ValidationError):
			setup.check_sheet()

	def test_a_client_named_by_id_is_found_by_its_name_and_linked_by_its_id(self):
		with named_by_id("Compliance Client"):
			known = frappe.get_doc(
				{"doctype": "Compliance Client", "client_name": "Bulk Test Group"}
			).insert()
			self.assertNotEqual(known.name, "Bulk Test Group")
			setup = frappe.get_doc({"doctype": "Compliance Setup Import"}).insert()
			frappe.get_doc(
				{
					"doctype": "File",
					"file_name": "companies.csv",
					"attached_to_doctype": setup.doctype,
					"attached_to_name": setup.name,
					"is_private": 1,
					"content": sheet(row(ID_COMPANY), row(TEST_COMPANY, client="Bulk Other Group", gstin="")),
				}
			).insert()
			setup.check_sheet()
			with patch("frappe.enqueue"):
				setup.start_import()
			with patch.object(frappe.db, "commit"):
				setup.run_import()
			self.assertEqual(
				frappe.db.get_value("Company Compliance Profile", ID_COMPANY, "client"), known.name
			)
			other = frappe.db.get_value("Company Compliance Profile", TEST_COMPANY, "client")
			self.assertEqual(
				frappe.db.get_value("Compliance Client", other, "client_name"), "Bulk Other Group"
			)
			self.assertNotEqual(other, "Bulk Other Group")

	def test_only_managers_import(self):
		with self.set_user(HOLDER), self.assertRaises(frappe.PermissionError):
			frappe.get_doc({"doctype": "Compliance Setup Import"}).insert()
		with self.set_user(MANAGER):
			frappe.get_doc({"doctype": "Compliance Setup Import"}).insert()
