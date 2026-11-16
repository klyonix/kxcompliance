# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.api import client_detail
from kxcompliance.install import create_standard_item_types
from kxcompliance.kx_compliance.doctype.compliance_client.test_compliance_client import (
	CLIENT_LOGIN,
	OTHER_COMPANY,
	SECOND_COMPANY,
	company,
	profile,
	with_login,
)
from kxcompliance.kx_compliance.doctype.compliance_item.compliance_item import DSC_TYPE
from kxcompliance.kx_compliance.doctype.signatory.signatory import signatories_for
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


def signatory(name: str = "Ravi Rao", company_name: str = TEST_COMPANY, **fields):
	return frappe.get_doc(
		{
			"doctype": "Signatory",
			"full_name": name,
			"company": company_name,
			"designation": "Director",
			**fields,
		}
	).insert()


def dsc(holder: str, company_name: str = TEST_COMPANY, **fields):
	return frappe.get_doc(
		{
			"doctype": "Compliance Item",
			"title": "DSC - Ravi Rao",
			"item_type": DSC_TYPE,
			"company": company_name,
			"holder_type": "Signatory",
			"holder": holder,
			"valid_from": "2025-01-10",
			"valid_until": "2027-01-09",
			"responsible": MANAGER,
			"dsc_class": "Class 3",
			**fields,
		}
	).insert()


class TestSignatory(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		create_standard_item_types()
		company(SECOND_COMPANY, "CTSC")
		company(OTHER_COMPANY, "CTOC")

	def setUp(self):
		frappe.db.delete("Compliance Item", {"item_type": DSC_TYPE})
		frappe.db.delete("Signatory")
		frappe.db.delete("Signatory Company")

	def test_din_and_pan_are_checked(self):
		with self.assertRaises(frappe.ValidationError):
			signatory(din="1234")
		with self.assertRaises(frappe.ValidationError):
			signatory(pan="ABCDE12345")
		ravi = signatory(din="01234567", pan="abcde1234f")
		self.assertEqual(ravi.pan, "ABCDE1234F")
		with self.assertRaises(frappe.ValidationError):
			signatory("Ravi R.", din="01234567")
		# The same person may be recorded again for another company.
		signatory("Ravi Rao", SECOND_COMPANY, din="01234567")

	def test_a_dsc_is_held_by_someone_who_signs_for_the_company(self):
		ravi = signatory(other_companies=[{"company": SECOND_COMPANY, "designation": "Director"}])
		item = dsc(ravi.name)
		self.assertEqual((item.holder_name, item.status), ("Ravi Rao", "Active"))
		dsc(ravi.name, SECOND_COMPANY)
		with self.assertRaises(frappe.ValidationError):
			dsc(ravi.name, OTHER_COMPANY)
		found = signatories_for("Signatory", "Rav", "full_name", 0, 20, {"company": SECOND_COMPANY})
		self.assertEqual([row[0] for row in found], [ravi.name])
		self.assertFalse(signatories_for("Signatory", "", "full_name", 0, 20, {"company": OTHER_COMPANY}))

	def test_hand_overs_keep_track_of_the_token(self):
		item = dsc(signatory().name)
		with self.freeze_time("2026-11-02"):
			item.hand_over("With the Firm", "Front office locker", "Received for GST filing")
		with self.freeze_time("2026-11-09"):
			item.hand_over("With the Holder", "Ravi Rao")
		self.assertEqual((item.custody, str(item.custody_since)), ("With the Holder", "2026-11-09"))
		self.assertEqual([row.recorded_by for row in item.custody_log], ["Administrator", "Administrator"])
		with self.assertRaises(frappe.ValidationError):
			item.hand_over("Lost")

	def test_the_client_sees_its_signatures_but_cannot_move_them(self):
		frappe.db.delete("Compliance Client Login")
		frappe.db.delete("Compliance Client Access")
		frappe.db.delete("Compliance Client Member")
		frappe.db.delete("Compliance Client")
		frappe.db.delete(
			"User Permission",
			{"user": ("in", [HOLDER, OTHER_HOLDER, MANAGER, CLIENT_LOGIN]), "allow": "Company"},
		)
		sunrise = with_login()
		profile(TEST_COMPANY, sunrise.name)
		item = dsc(signatory().name)
		item.hand_over("With the Firm")
		with self.set_user(CLIENT_LOGIN):
			signatures = client_detail(sunrise.name)["signatures"]
			self.assertEqual(
				[(row.name, row.holder_name, row.custody) for row in signatures],
				[(item.name, "Ravi Rao", "With the Firm")],
			)
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("Compliance Item", item.name).hand_over("With the Client")

	def test_the_clients_page_lists_its_signatories(self):
		frappe.db.delete("Compliance Client")
		sunrise = with_login()
		profile(TEST_COMPANY, sunrise.name)
		signatory()
		signatory("Former Director", is_active=0)
		signatory("Other Company Person", OTHER_COMPANY)
		people = [row.full_name for row in client_detail(sunrise.name)["signatories"]]
		self.assertEqual(people, ["Ravi Rao"])
