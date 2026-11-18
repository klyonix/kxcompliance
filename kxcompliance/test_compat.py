# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import json
from pathlib import Path

import frappe

from kxcompliance import compat
from kxcompliance.testing import IntegrationTestCase, UnitTestCase

DOCTYPES = Path(__file__).parent / "kx_compliance" / "doctype"


class TestCompat(UnitTestCase):
	def test_the_masked_fields_listed_are_those_the_doctypes_mask(self):
		for doctype, masked in compat.MASKED.items():
			definition = json.loads(
				(DOCTYPES / frappe.scrub(doctype) / f"{frappe.scrub(doctype)}.json").read_text()
			)
			fields = tuple(field["fieldname"] for field in definition["fields"] if field.get("mask"))
			roles = tuple(perm["role"] for perm in definition["permissions"] if perm.get("mask"))
			self.assertEqual((fields, roles), (masked["fields"], masked["roles"]))

	def test_an_aggregate_is_a_dict_on_16_and_sql_text_on_15(self):
		total = compat.agg("SUM", "late_fee", "late_fee")
		if compat.FRAPPE_MAJOR >= 16:
			self.assertEqual(total, {"SUM": "late_fee", "as": "late_fee"})
		else:
			self.assertEqual(total, "sum(late_fee) as late_fee")
		with self.assertRaises(ValueError):
			compat.agg("SUM", "late_fee); drop table x", "x")

	def test_the_desk_is_where_this_frappe_keeps_it(self):
		self.assertEqual(compat.DESK, "/desk" if compat.FRAPPE_MAJOR >= 16 else "/app")


class TestUserMenu(IntegrationTestCase):
	def test_the_app_is_first_in_the_user_menu_on_15_once(self):
		navbar = frappe.get_single("Navbar Settings")
		navbar.settings_dropdown = [
			row for row in navbar.settings_dropdown if row.route != compat.APP_MENU_ITEM["route"]
		]
		navbar.save()
		compat.add_the_app_to_the_user_menu()
		compat.add_the_app_to_the_user_menu()
		routes = [row.route for row in frappe.get_single("Navbar Settings").settings_dropdown]
		if compat.FRAPPE_MAJOR >= 16:
			self.assertNotIn("/compliance", routes)
		else:
			self.assertEqual(routes[0], "/compliance")
			self.assertEqual(routes.count("/compliance"), 1)
