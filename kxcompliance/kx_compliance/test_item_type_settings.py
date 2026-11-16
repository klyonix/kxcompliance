# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""A firm's own settings for an item type it may not change: used instead of the type's."""

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.api import (
	item_type_settings_of,
	item_types,
	save_item_type_settings,
	use_shared_item_type_settings,
)
from kxcompliance.kx_compliance.item_type_settings import types_in_use
from kxcompliance.kx_compliance.register import get_type_rules
from kxcompliance.kx_compliance.test_utils import (
	HOLDER,
	MANAGER,
	make_company,
	make_item,
	make_item_type,
	make_users,
)


class TestItemTypeSettings(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		cls.kind = make_item_type("Shared Test Licence", cycle=12, grace=0, reminders=(30,)).name

	def test_someone_who_may_change_the_type_changes_the_type(self):
		with self.set_user(MANAGER):
			shown = item_type_settings_of(self.kind)
		self.assertTrue(shown["may_edit_type"])
		self.assertFalse(shown["set_by_firm"])
		self.assertEqual(shown["reminders"], [30])

	def test_the_firms_own_settings_are_used_instead_of_the_types(self):
		with self.set_user(MANAGER):
			shown = save_item_type_settings(
				self.kind,
				{"is_active": 0, "renewal_cycle_months": 24, "grace_days": 15, "requires_document": 0},
				[60, 7],
			)
		self.assertTrue(shown["set_by_firm"])
		self.assertEqual(shown["reminders"], [60, 7])
		rules = get_type_rules([self.kind])[self.kind]
		self.assertEqual((rules.renewal_cycle_months, rules.grace_days), (24, 15))
		self.assertNotIn(self.kind, types_in_use())
		with self.set_user(MANAGER):
			listed = {row.name: row for row in item_types()}
		self.assertEqual((listed[self.kind].is_active, listed[self.kind].set_by_firm), (0, True))
		item = make_item(self.kind, days=200)
		self.assertEqual(sorted(row.days_before for row in item.reminders), [7, 60])
		# The type itself is left as it was.
		self.assertEqual(
			frappe.db.get_value("Compliance Item Type", self.kind, ["renewal_cycle_months", "is_active"]),
			(12, 1),
		)

	def test_going_back_to_the_shared_settings(self):
		with self.set_user(MANAGER):
			save_item_type_settings(
				self.kind,
				{"is_active": 1, "renewal_cycle_months": 6, "grace_days": 0, "requires_document": 1},
				[],
			)
		with self.set_user(HOLDER), self.assertRaises(frappe.PermissionError):
			use_shared_item_type_settings(self.kind)
		with self.set_user(MANAGER):
			shown = use_shared_item_type_settings(self.kind)
		self.assertFalse(shown["set_by_firm"])
		self.assertEqual(get_type_rules([self.kind])[self.kind].renewal_cycle_months, 12)

	def test_only_the_settings_a_firm_may_keep_are_taken(self):
		with self.set_user(MANAGER), self.assertRaises(frappe.ValidationError):
			save_item_type_settings(self.kind, {"category": "Insurance"}, [])
