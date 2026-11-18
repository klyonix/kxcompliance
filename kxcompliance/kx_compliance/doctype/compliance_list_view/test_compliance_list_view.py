# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe

from kxcompliance.kx_compliance.test_utils import HOLDER, MANAGER, OTHER_HOLDER, make_users
from kxcompliance.testing import IntegrationTestCase

IGNORE_TEST_RECORD_DEPENDENCIES = ["User"]
test_ignore = IGNORE_TEST_RECORD_DEPENDENCIES  # the name Frappe 15 reads


def view(label="Mine", **fields):
	return frappe.get_doc(
		{
			"doctype": "Compliance List View",
			"label": label,
			"list_key": "register",
			"layout": "Table",
			"filters": '[["item_type", "=", "FSSAI Licence"]]',
			**fields,
		}
	).insert()


class TestComplianceListView(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_users()

	def setUp(self):
		frappe.db.delete("Compliance List View")

	def test_a_view_is_its_owners_until_a_manager_shares_it(self):
		with self.set_user(HOLDER):
			mine = view()
		with self.set_user(OTHER_HOLDER):
			self.assertEqual(frappe.get_list("Compliance List View", pluck="name"), [])
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("Compliance List View", mine.name).check_permission("read")
		with self.set_user(MANAGER):
			shared = view("Everyone's FSSAI", is_shared=1, is_pinned=1)
		with self.set_user(OTHER_HOLDER):
			self.assertEqual(frappe.get_list("Compliance List View", pluck="name"), [shared.name])
			doc = frappe.get_doc("Compliance List View", shared.name)
			doc.label = "Renamed"
			with self.assertRaises(frappe.PermissionError):
				doc.save()

	def test_only_a_manager_shares_or_pins(self):
		with self.set_user(HOLDER):
			with self.assertRaisesRegex(frappe.PermissionError, "Only a Compliance Manager"):
				view(is_shared=1)
			mine = view()
			mine.is_pinned = 1
			with self.assertRaisesRegex(frappe.PermissionError, "Only a Compliance Manager"):
				mine.save()
		with self.set_user(MANAGER):
			pinned = view("Pinned", is_pinned=1)
			self.assertEqual(pinned.is_shared, 1)

	def test_a_view_needs_a_name_valid_state_and_a_board_for_kanban(self):
		with self.set_user(HOLDER):
			with self.assertRaisesRegex(frappe.ValidationError, "Give the view a name"):
				view("  ")
			with self.assertRaisesRegex(frappe.ValidationError, "Choose the board"):
				view(layout="Kanban")
			with self.assertRaisesRegex(frappe.ValidationError, "not valid"):
				view(filters="{not json")
