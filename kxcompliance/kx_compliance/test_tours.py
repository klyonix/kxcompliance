# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe

from kxcompliance.api import tour_opened, tours_seen
from kxcompliance.kx_compliance.test_utils import HOLDER, MANAGER, make_users
from kxcompliance.testing import IntegrationTestCase


class TestTours(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_users()

	def setUp(self):
		frappe.db.delete("Compliance Tour View")

	def test_a_tour_is_seen_once_opened_and_every_replay_counted(self):
		with self.set_user(HOLDER):
			self.assertEqual(tours_seen(), {"seen": []})
			self.assertEqual(tour_opened("filings")["times_opened"], 1)
			self.assertEqual(tour_opened("filings")["times_opened"], 2)
			self.assertEqual(tours_seen(), {"seen": ["filings"]})
		with self.set_user(MANAGER):
			self.assertEqual(tours_seen(), {"seen": []})

	def test_only_known_tours_and_people_of_the_app(self):
		with self.set_user(HOLDER), self.assertRaisesRegex(frappe.ValidationError, "no tour"):
			tour_opened("not-a-tour")
		with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
			tours_seen()
