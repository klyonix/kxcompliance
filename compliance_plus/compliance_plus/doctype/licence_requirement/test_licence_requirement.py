# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from compliance_plus.api import can_open_app, check_party, has_app_access, my_work, search_parties
from compliance_plus.compliance_plus.move_old_trackers import (
	CUSTOMER_LICENCE_TABLES,
	move_customer_licence_row,
)
from compliance_plus.compliance_plus.party_dashboards import customer as customer_dashboard
from compliance_plus.compliance_plus.party_licences import check_document, override_key
from compliance_plus.compliance_plus.reminders import send_party_reminders
from compliance_plus.compliance_plus.test_utils import (
	HOLDER,
	TEST_COMPANY,
	make_company,
	make_user,
	make_users,
)

# These tests build their own records; skip ERPNext's generated ones.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Compliance Item Type", "Item Group", "Customer Group", "Supplier Group"]

PHARMACY = "Licence Test Pharmacy"
GROCER = "Licence Test Grocer"
WHOLESALER = "Licence Test Wholesaler"
DRUGS = "Licence Test Drugs"
SNACKS = "Licence Test Snacks"
CHEMISTS = "Licence Test Chemists"
SALES = "licence-sales@example.com"


def ensure_tree(doctype: str, root: str, name: str, parent_field: str):
	if not frappe.db.exists(doctype, root):
		frappe.get_doc({"doctype": doctype, frappe.scrub(doctype) + "_name": root, "is_group": 1}).insert()
	if not frappe.db.exists(doctype, name):
		frappe.get_doc(
			{"doctype": doctype, frappe.scrub(doctype) + "_name": name, parent_field: root}
		).insert()


def make_party(doctype: str, name: str, **fields):
	if not frappe.db.exists(doctype, name):
		frappe.get_doc({"doctype": doctype, frappe.scrub(doctype) + "_name": name, **fields}).insert()
	return name


def licence(holder_type: str, holder: str, item_type: str, valid_until: str, number: str = "20B-KA-0001"):
	return frappe.get_doc(
		{
			"doctype": "Compliance Item",
			"title": f"{item_type} {holder}",
			"item_type": item_type,
			"company": TEST_COMPANY,
			"holder_type": holder_type,
			"holder": holder,
			"reference_number": number,
			"valid_until": valid_until,
			"responsible": HOLDER,
		}
	).insert()


def requirement(**fields):
	values = {
		"doctype": "Licence Requirement",
		"item_type": "Drug Licence",
		"party_type": "Customer",
		"action": "Block",
		"item_groups": [{"item_group": DRUGS}],
	}
	values.update(fields)
	return frappe.get_doc(values).insert()


def sales_order(
	customer: str = PHARMACY, item_group: str = DRUGS, day: str = "2026-11-14", name: str | None = None
):
	doc = frappe.get_doc(
		{
			"doctype": "Sales Order",
			"customer": customer,
			"transaction_date": day,
			"items": [{"item_code": "anything", "item_group": item_group}],
		}
	)
	if name:
		doc.name = name
	else:
		doc.set("__islocal", 1)
	return doc


def make_parties():
	make_company()
	make_users()
	frappe.defaults.set_global_default("company", TEST_COMPANY)
	ensure_tree("Item Group", "All Item Groups", DRUGS, "parent_item_group")
	ensure_tree("Item Group", "All Item Groups", SNACKS, "parent_item_group")
	ensure_tree("Customer Group", "All Customer Groups", CHEMISTS, "parent_customer_group")
	ensure_tree("Supplier Group", "All Supplier Groups", "Licence Test Suppliers", "parent_supplier_group")
	make_party("Customer", PHARMACY, customer_group=CHEMISTS, email_id="pharmacy@example.com")
	make_party("Customer", GROCER)
	make_party("Supplier", WHOLESALER, supplier_group="Licence Test Suppliers")


class TestLicenceRequirement(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_parties()

	def setUp(self):
		# Data stays until the class ends, so clear what an earlier test may have left.
		frappe.db.delete("Licence Requirement")
		frappe.db.delete("Licence Override")
		frappe.db.delete("Licence Check Log")
		frappe.db.delete("Compliance Item", {"holder_type": ("in", ["Customer", "Supplier"])})

	def test_a_sale_without_the_licence_is_blocked(self):
		requirement()
		with self.assertRaisesRegex(frappe.ValidationError, "has no Drug Licence on record"):
			check_document(sales_order(), "validate")

	def test_an_expired_licence_blocks_and_a_valid_one_passes(self):
		requirement()
		licence("Customer", PHARMACY, "Drug Licence", "2026-10-31")
		with self.assertRaisesRegex(frappe.ValidationError, "expired on"):
			check_document(sales_order(), "validate")
		licence("Customer", PHARMACY, "Drug Licence", "2027-10-31", number="20B-KA-0002")
		check_document(sales_order(), "validate")

	def test_grace_days_let_a_recently_expired_licence_count(self):
		requirement(grace_days=30)
		licence("Customer", PHARMACY, "Drug Licence", "2026-10-31")
		check_document(sales_order(), "validate")

	def test_a_requirement_applies_only_to_its_item_and_customer_groups(self):
		requirement(party_groups=[{"party_group": CHEMISTS}])
		check_document(sales_order(item_group=SNACKS), "validate")
		check_document(sales_order(customer=GROCER), "validate")
		with self.assertRaises(frappe.ValidationError):
			check_document(sales_order(), "validate")

	def test_a_document_type_left_unticked_is_not_checked(self):
		requirement(check_sales_order=0)
		check_document(sales_order(), "validate")

	def test_warn_lets_the_document_through_and_is_logged_on_submit(self):
		requirement(action="Warn")
		doc = sales_order(name="SO-LICENCE-TEST-1")
		check_document(doc, "validate")
		self.assertIn("Drug Licence", str(frappe.message_log))
		check_document(doc, "on_submit")
		self.assertEqual(
			frappe.get_all("Licence Check Log", filters={"reference_name": doc.name}, pluck="result"),
			["Warned"],
		)

	def test_an_override_lets_one_document_through(self):
		requirement()
		override = frappe.get_doc(
			{
				"doctype": "Licence Override",
				"reference_doctype": "Sales Order",
				"reference_name": "SO-LICENCE-TEST-2",
				"override_key": override_key("Sales Order", "SO-LICENCE-TEST-2"),
				"reason": "Renewal filed, certificate awaited",
			}
		)
		override.flags.ignore_validate = True
		override.flags.ignore_links = True  # the Sales Order is never saved in this test
		override.insert()
		check_document(sales_order(name="SO-LICENCE-TEST-2"), "validate")
		with self.assertRaises(frappe.ValidationError):
			check_document(sales_order(name="SO-LICENCE-TEST-3"), "validate")

	def test_an_override_needs_a_real_document_and_a_reason(self):
		override = frappe.get_doc(
			{
				"doctype": "Licence Override",
				"reference_doctype": "Sales Order",
				"reference_name": "SO-DOES-NOT-EXIST",
				"reason": "x",
			}
		)
		with self.assertRaisesRegex(frappe.ValidationError, "Could not find|does not exist"):
			override.insert()

	def test_supplier_licences_are_checked_on_purchases(self):
		requirement(party_type="Supplier", item_groups=[])
		order = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": WHOLESALER,
				"transaction_date": "2026-11-14",
				"items": [],
			}
		)
		with self.assertRaisesRegex(frappe.ValidationError, "Supplier"):
			check_document(order, "validate")

	def test_the_invoice_carries_the_customer_licence_numbers(self):
		licence("Customer", PHARMACY, "Drug Licence", "2027-10-31", number="20B-KA-0099")
		invoice = frappe.get_doc(
			{"doctype": "Sales Invoice", "customer": PHARMACY, "posting_date": "2026-11-14", "items": []}
		)
		check_document(invoice, "validate")
		self.assertIn("Drug Licence: 20B-KA-0099", invoice.customer_licence_numbers)

	def test_the_customer_dashboard_lists_licences(self):
		data = customer_dashboard(frappe._dict({"fieldname": "customer", "transactions": []}))
		self.assertEqual(data["non_standard_fieldnames"]["Compliance Item"], "holder")
		self.assertEqual(data["dynamic_links"]["holder"], ["Customer", "holder_type"])

	def test_the_check_is_hooked_on_every_document(self):
		hooks = frappe.get_hooks("doc_events")
		for doctype in (
			"Quotation",
			"Sales Order",
			"Delivery Note",
			"Sales Invoice",
			"Purchase Order",
			"Purchase Receipt",
			"Purchase Invoice",
		):
			self.assertIn(
				"compliance_plus.compliance_plus.party_licences.check_document", hooks[doctype]["validate"]
			)

	def test_customers_are_reminded_once_before_their_licence_expires(self):
		licence("Customer", PHARMACY, "Drug Licence", "2026-11-20")
		if not frappe.db.exists("Email Template", "Licence Test Reminder"):
			frappe.get_doc(
				{
					"doctype": "Email Template",
					"name": "Licence Test Reminder",
					"subject": "Your {{ doc.item_type }} expires on {{ valid_until }}",
					"response": "Dear {{ party_name }}, please renew.",
				}
			).insert()
		account = frappe.get_doc(
			{
				"doctype": "Email Account",
				"email_account_name": "Licence Test",
				"email_id": "licences@example.com",
			}
		)
		account.flags.ignore_validate = True
		account.insert()
		with (
			self.change_settings(
				"Compliance Plus Settings",
				party_email_template="Licence Test Reminder",
				email_account=account.name,
			),
			patch("frappe.sendmail") as sendmail,
			self.freeze_time("2026-11-14"),
		):
			send_party_reminders(frappe.utils.getdate("2026-11-14"))
			send_party_reminders(frappe.utils.getdate("2026-11-14"))
		self.assertEqual(sendmail.call_count, 1)
		self.assertEqual(sendmail.call_args.kwargs["recipients"], ["pharmacy@example.com"])
		self.assertIn("Drug Licence", sendmail.call_args.kwargs["subject"])

	def test_old_customer_licence_rows_become_register_items(self):
		# The old tables exist only on the client's site; a ToDo stands in as the source record.
		source = frappe.get_doc({"doctype": "ToDo", "description": "old drug licence row"}).insert()
		row = frappe._dict(
			name=source.name,
			parent=PHARMACY,
			license_number="20B-KA-OLD",
			expiry_date="2027-03-31",
			component="Retail",
			owner="Administrator",
			in_charge=None,
			description=None,
		)
		with patch.dict(CUSTOMER_LICENCE_TABLES, {"ToDo": "Drug Licence"}):
			name = move_customer_licence_row("ToDo", row, TEST_COMPANY)
		item = frappe.get_doc("Compliance Item", name)
		self.assertEqual(
			(item.holder_type, item.holder, item.item_type), ("Customer", PHARMACY, "Drug Licence")
		)
		self.assertEqual(item.reference_number, "20B-KA-OLD")
		self.assertIn("Retail", item.notes)


class TestLicenceCheckScreen(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_parties()
		make_user(SALES, ("Sales User",))

	def setUp(self):
		frappe.db.delete("Licence Requirement")
		frappe.db.delete("Compliance Item", {"holder_type": ("in", ["Customer", "Supplier"])})

	def requirement_for(self, result: dict, item_type: str) -> dict:
		return next(row for row in result["requirements"] if row["item_type"] == item_type)

	def test_the_check_says_which_licences_are_missing_expired_or_in_order(self):
		requirement(party_groups=[{"party_group": CHEMISTS}], check_quotation=0)
		requirement(item_type="FSSAI Licence", item_groups=[], action="Warn", grace_days=15)
		with self.freeze_time("2026-11-14"):
			result = check_party("Customer", PHARMACY)
			drug = self.requirement_for(result, "Drug Licence")
			self.assertEqual(drug["result"], "missing")
			self.assertEqual(drug["item_groups"], [DRUGS])
			self.assertNotIn("Quotation", drug["documents"])
			self.assertIn("Sales Invoice", drug["documents"])

			licence("Customer", PHARMACY, "Drug Licence", "2026-11-01")
			licence("Customer", PHARMACY, "FSSAI Licence", "2026-11-05", number="FS-1")
			result = check_party("Customer", PHARMACY)
			self.assertEqual(self.requirement_for(result, "Drug Licence")["result"], "expired")
			# Expired nine days ago, inside its fifteen days of grace.
			self.assertEqual(self.requirement_for(result, "FSSAI Licence")["result"], "ok")
			self.assertEqual(len(result["licences"]), 2)
			self.assertFalse(any(row["valid"] for row in result["licences"]))

			# A requirement limited to chemists does not apply to a grocer.
			grocer = check_party("Customer", GROCER)
			self.assertEqual([row["item_type"] for row in grocer["requirements"]], ["FSSAI Licence"])

	def test_sales_staff_check_customers_only_and_see_nothing_else(self):
		with self.set_user(SALES):
			self.assertTrue(can_open_app())
			self.assertFalse(has_app_access())
			self.assertIn(PHARMACY, [row.name for row in search_parties("Customer", "Pharmacy")])
			self.assertEqual(check_party("Customer", PHARMACY)["party"], PHARMACY)
			with self.assertRaises(frappe.PermissionError):
				check_party("Supplier", WHOLESALER)
			with self.assertRaises(frappe.PermissionError):
				search_parties("Supplier", "")
			with self.assertRaises(frappe.PermissionError):
				my_work()

	def test_compliance_staff_search_both_sides_without_reading_parties(self):
		with self.set_user(HOLDER):
			self.assertFalse(frappe.has_permission("Customer", "read"))
			found = search_parties("Supplier", "wholesale")
			self.assertEqual([row.name for row in found], [WHOLESALER])
			self.assertEqual(found[0].party_group, "Licence Test Suppliers")
			self.assertEqual(check_party("Customer", GROCER)["party_name"], GROCER)
