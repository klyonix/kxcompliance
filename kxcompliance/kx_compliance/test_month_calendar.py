# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.api import month_events
from kxcompliance.kx_compliance.test_bulk_filing import filing
from kxcompliance.kx_compliance.test_utils import (
	HOLDER,
	MANAGER,
	OTHER_HOLDER,
	TEST_COMPANY,
	make_company,
	make_item,
	make_item_type,
	make_users,
)

NOVEMBER = ("2026-11-01", "2026-11-30")


class TestMonthCalendar(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		make_item_type("Test Calendar Licence", grace=0)

	def setUp(self):
		frappe.db.delete("Compliance Task")
		frappe.db.delete("Compliance Item", {"company": TEST_COMPANY})

	def test_a_month_holds_filings_and_expiries_on_their_days(self):
		open_filing = filing("GSTR-3B (Monthly)", "2026-10-31", "2026-11-20")
		filed = filing("GSTR-1 (Monthly)", "2026-10-31", "2026-11-11", status="Filed")
		filing("GSTR-3B (Monthly)", "2026-11-30", "2026-12-20")  # next month
		filing("GSTR-1 (Monthly)", "2026-09-30", "2026-11-11", status="Not Applicable")
		item = make_item("Test Calendar Licence", valid_until="2026-11-15")
		with self.set_user(MANAGER):
			events = month_events(*NOVEMBER)
		self.assertEqual(
			[(event["kind"], event["name"], event["date"]) for event in events],
			[
				("filing", filed, "2026-11-11"),
				("licence", item.name, "2026-11-15"),
				("filing", open_filing, "2026-11-20"),
			],
		)
		self.assertTrue(events[0]["done"])
		self.assertFalse(events[2]["done"])

	def test_the_client_filter_and_permissions_narrow_it(self):
		mine = filing("GSTR-3B (Monthly)", "2026-10-31", "2026-11-20")
		filing("GSTR-1 (Monthly)", "2026-10-31", "2026-11-11", responsible=OTHER_HOLDER)
		with self.set_user(HOLDER):
			self.assertEqual([event["name"] for event in month_events(*NOVEMBER)], [mine])
		with self.set_user(MANAGER):
			self.assertEqual(month_events(*NOVEMBER, companies='["Another Company"]'), [])
			self.assertEqual(len(month_events(*NOVEMBER, companies=f'["{TEST_COMPANY}"]')), 2)
			with self.assertRaises(frappe.ValidationError):
				month_events(*NOVEMBER, companies='{"company": ["!=", ""]}')

	def test_it_refuses_a_range_longer_than_a_month_grid(self):
		with self.set_user(MANAGER), self.assertRaisesRegex(frappe.ValidationError, "up to 45 days"):
			month_events("2026-01-01", "2026-12-31")
