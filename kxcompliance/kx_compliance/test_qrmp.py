# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.api import fixed_sum
from kxcompliance.kx_compliance.test_utils import (
	HOLDER,
	MANAGER,
	OTHER_HOLDER,
	TEST_COMPANY,
	make_company,
	make_users,
)


def filing(template: str, period_start: str, period_end: str, status: str = "Open", **fields) -> str:
	name = (
		frappe.get_doc(
			{
				"doctype": "Compliance Task",
				"obligation_template": template,
				"company": TEST_COMPANY,
				"registration_number": "29GST",
				"period_start": period_start,
				"period_end": period_end,
				"period_label": period_end[:7],
				"due_date": period_end,
				"status": "Open",
				"responsible": HOLDER,
				"task_key": f"qrmp-test|{template}|{period_end}|{frappe.generate_hash(length=6)}",
			}
		)
		.insert()
		.name
	)
	if status != "Open" or fields:
		# Only the status and amount matter here; filing it properly needs proof and a review.
		frappe.db.set_value("Compliance Task", name, {"status": status, **fields})
	return name


class TestQrmpFixedSum(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()

	def setUp(self):
		frappe.db.delete("Compliance Task", {"company": TEST_COMPANY})

	def test_the_fixed_sum_is_35_percent_of_the_last_quarters_cash_tax(self):
		filing("GSTR-3B (QRMP, 22nd)", "2026-07-01", "2026-09-30", "Filed", amount_paid=100001)
		october = filing("PMT-06 (QRMP Monthly Payment)", "2026-10-01", "2026-10-31")
		with self.set_user(MANAGER):
			result = fixed_sum(october)
		self.assertEqual(result["amount"], 35000)
		self.assertEqual(result["percent"], 35)
		self.assertIn("GSTR-3B (QRMP, 22nd)", result["from_label"])

	def test_after_filing_monthly_it_is_all_of_the_last_months_tax(self):
		filing("GSTR-3B (Monthly)", "2026-08-01", "2026-08-31", "Filed", amount_paid=9000)
		filing("GSTR-3B (Monthly)", "2026-09-01", "2026-09-30", "Filed Late", amount_paid=12000)
		november = filing("PMT-06 (QRMP Monthly Payment)", "2026-11-01", "2026-11-30")
		with self.set_user(MANAGER):
			result = fixed_sum(november)
		self.assertEqual((result["amount"], result["percent"]), (12000, 100))

	def test_without_a_filed_return_for_last_quarter_there_is_no_fixed_sum(self):
		filing("GSTR-3B (QRMP, 22nd)", "2026-07-01", "2026-09-30", amount_paid=50000)  # not filed
		october = filing("PMT-06 (QRMP Monthly Payment)", "2026-10-01", "2026-10-31")
		with self.set_user(MANAGER):
			result = fixed_sum(october)
		self.assertIsNone(result["amount"])
		self.assertEqual(result["previous_period"], "Sep 2026")

	def test_only_a_pmt_06_filing_has_one_and_only_for_those_who_may_read_it(self):
		gstr3b = filing("GSTR-3B (Monthly)", "2026-10-01", "2026-10-31")
		october = filing("PMT-06 (QRMP Monthly Payment)", "2026-10-01", "2026-10-31")
		with self.set_user(MANAGER):
			self.assertIsNone(fixed_sum(gstr3b))
		with self.set_user(OTHER_HOLDER), self.assertRaises(frappe.PermissionError):
			fixed_sum(october)
