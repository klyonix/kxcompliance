# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.api import bulk_filing_choices, nil_filing_choices
from kxcompliance.kx_compliance.test_utils import (
	HOLDER,
	MANAGER,
	OTHER_HOLDER,
	TEST_COMPANY,
	make_company,
	make_users,
)


def filing(template: str, period_end: str, due_date: str, responsible: str = HOLDER, status: str = "Open"):
	name = (
		frappe.get_doc(
			{
				"doctype": "Compliance Task",
				"obligation_template": template,
				"company": TEST_COMPANY,
				"period_start": period_end[:8] + "01",
				"period_end": period_end,
				"period_label": period_end[:7],
				"due_date": due_date,
				"status": "Open",
				"responsible": responsible,
				"task_key": f"bulk-test|{template}|{frappe.generate_hash(length=6)}",
			}
		)
		.insert()
		.name
	)
	if status != "Open":
		# Only the status matters here; filing it properly needs proof and a review.
		frappe.db.set_value("Compliance Task", name, "status", status)
	return name


class TestBulkFiling(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()

	def setUp(self):
		frappe.db.delete("Compliance Task")

	def test_choices_group_open_filings_by_return_and_period_soonest_first(self):
		filing("GSTR-3B (Monthly)", "2026-11-30", "2026-12-20")
		filing("GSTR-3B (Monthly)", "2026-11-30", "2026-12-20", status="Ready for Review")
		filing("GSTR-3B (Monthly)", "2026-11-30", "2026-12-20", status="Filed")
		filing("GSTR-1 (Monthly)", "2026-11-30", "2026-12-11")
		filing("GSTR-3B (Monthly)", "2026-10-31", "2026-11-20", status="Not Applicable")
		with self.set_user(MANAGER):
			choices = bulk_filing_choices()
		self.assertEqual(
			[(row["obligation_template"], row["period_end"], row["filings"]) for row in choices],
			[("GSTR-1 (Monthly)", "2026-11-30", 1), ("GSTR-3B (Monthly)", "2026-11-30", 2)],
		)
		self.assertEqual(choices[0]["due"], "2026-12-11")

	def test_a_compliance_user_is_offered_only_their_own_filings(self):
		filing("GSTR-3B (Monthly)", "2026-11-30", "2026-12-20")
		filing("GSTR-1 (Monthly)", "2026-11-30", "2026-12-11", responsible=OTHER_HOLDER)
		with self.set_user(HOLDER):
			choices = bulk_filing_choices()
		self.assertEqual([row["obligation_template"] for row in choices], ["GSTR-3B (Monthly)"])

	def test_nil_choices_are_the_companies_with_nil_returns_still_to_file(self):
		for name in (
			filing("GSTR-3B (Monthly)", "2026-10-31", "2026-11-20"),
			filing("GSTR-1 (Monthly)", "2026-10-31", "2026-11-11"),
			filing("GSTR-3B (Monthly)", "2026-09-30", "2026-10-20", status="Filed"),
		):
			frappe.db.set_value("Compliance Task", name, "is_nil", 1)
		filing("GSTR-3B (Monthly)", "2026-11-30", "2026-12-20")  # not NIL
		with self.set_user(MANAGER):
			choices = nil_filing_choices()
		self.assertEqual(choices, [{"company": TEST_COMPANY, "due": "2026-11-11", "filings": 2}])
