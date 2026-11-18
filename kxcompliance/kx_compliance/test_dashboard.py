# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days

from kxcompliance.kx_compliance.dashboard import get_dashboard
from kxcompliance.kx_compliance.test_utils import (
	HOLDER,
	MANAGER,
	OTHER_HOLDER,
	make_company,
	make_item,
	make_item_type,
	make_users,
)
from kxcompliance.testing import IntegrationTestCase

TODAY = "2026-06-01"


class TestDashboard(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		make_item_type("Test Dashboard Licence")

	def setUp(self):
		frappe.db.delete("Compliance Item", {"item_type": "Test Dashboard Licence"})

	def test_late_and_soon_are_counted_by_their_dates(self):
		with self.freeze_time(TODAY):
			make_item("Test Dashboard Licence", valid_until="2026-05-20", responsible=HOLDER)
			make_item("Test Dashboard Licence", valid_until="2026-06-05", responsible=HOLDER)
			make_item("Test Dashboard Licence", valid_until="2026-06-20", responsible=HOLDER)
			with self.set_user(MANAGER):
				board = get_dashboard(TODAY)
		tiles = {tile["key"]: tile for tile in board["urgency"]}
		renewals = {key: tile["parts"][1] for key, tile in tiles.items() if key != "review"}
		self.assertGreaterEqual(renewals["overdue"]["value"], 1)
		self.assertGreaterEqual(renewals["week"]["value"], 1)
		self.assertGreaterEqual(renewals["month"]["value"], 1)
		self.assertIn(["valid_until", "<", TODAY], renewals["overdue"]["filters"])
		self.assertEqual(tiles["overdue"]["value"], sum(part["value"] for part in tiles["overdue"]["parts"]))
		self.assertEqual(len(board["due_by_month"]), 6)
		self.assertEqual(board["due_by_month"][0]["month"], "Jun 2026")
		self.assertGreaterEqual(board["due_by_month"][0]["Renewals"], 2)
		self.assertEqual(len(board["filed_by_month"]), 6)
		self.assertEqual(board["filed_by_month"][-1]["month"], "Jun 2026")

	def test_the_activity_feed_shows_only_records_the_person_may_read(self):
		with self.freeze_time(TODAY):
			item = make_item("Test Dashboard Licence", valid_until=add_days(TODAY, 200), responsible=HOLDER)
			item.notes = "Changed"
			# Frappe keeps no change history in tests unless asked.
			item.save(ignore_version=False)
		with self.set_user(MANAGER):
			self.assertIn(item.name, [entry["name"] for entry in get_dashboard(TODAY)["recent"]])
		with self.set_user(OTHER_HOLDER):
			self.assertNotIn(item.name, [entry["name"] for entry in get_dashboard(TODAY)["recent"]])
