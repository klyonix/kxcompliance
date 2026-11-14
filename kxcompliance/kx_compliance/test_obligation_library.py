# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.api import extension_preview, obligation_form_options
from kxcompliance.kx_compliance.obligation_library import sync_standard_templates
from kxcompliance.kx_compliance.test_utils import (
	HOLDER,
	MANAGER,
	TEST_COMPANY,
	make_company,
	make_users,
)

TEMPLATE = "Compliance Obligation Template"
GSTR_3B = "GSTR-3B (Monthly)"


def filing(period_end: str, due_date: str, filed: bool = False) -> str:
	name = (
		frappe.get_doc(
			{
				"doctype": "Compliance Task",
				"obligation_template": GSTR_3B,
				"company": TEST_COMPANY,
				"period_start": period_end[:8] + "01",
				"period_end": period_end,
				"period_label": period_end[:7],
				"due_date": due_date,
				"status": "Open",
				"responsible": HOLDER,
				"task_key": f"library-test|{period_end}|{frappe.generate_hash(length=6)}",
			}
		)
		.insert()
		.name
	)
	if filed:
		# Filing needs proof and a review; only the status matters here.
		frappe.db.set_value("Compliance Task", name, "status", "Filed")
	return name


def extend(periods_from: str, periods_to: str, new_due_date: str, reference: str = "Test 1/2026"):
	return frappe.get_doc(
		{
			"doctype": "Compliance Due Date Extension",
			"obligation_template": GSTR_3B,
			"periods_ending_from": periods_from,
			"periods_ending_to": periods_to,
			"new_due_date": new_due_date,
			"notification_reference": reference,
		}
	).insert()


def due(task: str) -> tuple[str, str | None]:
	values = frappe.db.get_value("Compliance Task", task, ["effective_due_date", "extension"], as_dict=True)
	return str(values.effective_due_date), values.extension


class TestObligationLibrary(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()

	def setUp(self):
		frappe.db.delete("Compliance Task", {"company": TEST_COMPANY})
		frappe.db.delete("Compliance Due Date Extension", {"obligation_template": GSTR_3B})

	def test_a_standard_obligation_keeps_its_rules(self):
		doc = frappe.get_doc(TEMPLATE, GSTR_3B)
		doc.due_day = 25
		with self.assertRaisesRegex(frappe.ValidationError, "standard obligation.*Due Day"):
			doc.save()
		doc.reload()
		doc.append("reminders", {"days_before": 30})
		with self.assertRaisesRegex(frappe.ValidationError, "Reminders"):
			doc.save()

	def test_a_firm_may_switch_it_off_and_set_its_own_figures(self):
		doc = frappe.get_doc(TEMPLATE, GSTR_3B)
		doc.is_active = 0
		doc.save()
		self.assertFalse(doc.penalty_set_by_firm)
		doc.late_fee_per_day = 20
		doc.save()
		self.assertTrue(doc.penalty_set_by_firm)
		sync_standard_templates()
		self.assertEqual(frappe.db.get_value(TEMPLATE, GSTR_3B, ["late_fee_per_day", "is_active"]), (20, 0))

	def test_going_back_to_the_library_figures(self):
		frappe.db.set_value(TEMPLATE, GSTR_3B, {"late_fee_per_day": 20, "penalty_set_by_firm": 1})
		doc = frappe.get_doc(TEMPLATE, GSTR_3B)
		with self.set_user(HOLDER), self.assertRaises(frappe.PermissionError):
			doc.use_library_figures()
		with self.set_user(MANAGER):
			doc.use_library_figures()
		self.assertEqual(
			frappe.db.get_value(TEMPLATE, GSTR_3B, ["late_fee_per_day", "penalty_set_by_firm"]), (50, 0)
		)

	def test_a_firms_own_obligation_is_fully_editable_and_never_standard(self):
		doc = frappe.get_doc(
			{
				"doctype": TEMPLATE,
				"template_name": "Test Local Body Return",
				"law": "Other",
				"frequency": "Quarterly",
				"period_basis": "Financial Year",
				"months_after_period": 1,
				"due_day": 15,
				"is_standard": 1,
			}
		).insert()
		self.assertFalse(doc.is_standard)
		doc.due_day = 20
		doc.save()

	def test_narrowing_an_extension_sends_filings_back(self):
		october = filing("2026-10-31", "2026-11-20")
		november = filing("2026-11-30", "2026-12-20")
		filed = filing("2026-11-30", "2026-12-20", filed=True)
		wide = extend("2026-10-01", "2026-11-30", "2026-12-31")
		self.assertEqual(due(october), ("2026-12-31", wide.name))
		self.assertEqual(due(november), ("2026-12-31", wide.name))

		other = extend("2026-11-01", "2026-11-30", "2026-12-27", reference="Test 2/2026")
		wide.periods_ending_to = "2026-10-31"
		wide.save()
		self.assertEqual(due(october), ("2026-12-31", wide.name))
		self.assertEqual(due(november), ("2026-12-27", other.name))

		other.periods_ending_from = other.periods_ending_to = "2026-12-31"
		other.save()
		self.assertEqual(due(november), ("2026-12-20", None))
		self.assertEqual(due(filed), ("2026-12-20", None))

	def test_the_preview_counts_open_filings_for_managers_only(self):
		filing("2026-10-31", "2026-11-20")
		filing("2026-11-30", "2026-12-20")
		filing("2026-11-30", "2026-12-20", filed=True)
		with self.set_user(MANAGER):
			self.assertEqual(
				extension_preview(GSTR_3B, "2026-10-01", "2026-11-30"), {"filings": 2, "companies": 1}
			)
			options = obligation_form_options()
		self.assertIn("GST", options["law"])
		self.assertIn("Private Limited", options["company_types"])
		self.assertIn("Karnataka", options["states"])
		with self.set_user(HOLDER):
			with self.assertRaises(frappe.PermissionError):
				extension_preview(GSTR_3B, "2026-10-01", "2026-11-30")
			with self.assertRaises(frappe.PermissionError):
				obligation_form_options()
