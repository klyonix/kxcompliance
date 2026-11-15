# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.api import (
	app_companies,
	bill,
	bill_options,
	billing_setup,
	cancel_bill,
	client_fees,
	create_bill,
	save_return_fees,
	send_bill,
	set_up_billing,
)
from kxcompliance.kx_compliance.billing import OUTSIDE_STATE, WITHIN_STATE, make_monthly_drafts, state_of
from kxcompliance.kx_compliance.companies import companies_overview
from kxcompliance.kx_compliance.doctype.compliance_client.test_compliance_client import client, profile
from kxcompliance.kx_compliance.register import compliance_companies
from kxcompliance.kx_compliance.test_bulk_filing import filing
from kxcompliance.kx_compliance.test_utils import (
	HOLDER,
	MANAGER,
	TEST_COMPANY,
	make_company,
	make_user,
	make_users,
)

SETTINGS = "KX Compliance Settings"
ACCOUNTS = "billing-accounts@example.com"
FIRM = "Billing Test Associates"
DETAILS = {
	"billing_gstin": "29aaaca1234f1z5",
	"billing_address": "12 MG Road, Bengaluru",
	"bank_details": "Test Bank, A/c 0001, IFSC TEST0000001",
	"bill_prefix": "BTA",
}


def rates(company: str, title: str) -> list[tuple[str, float]]:
	template = frappe.db.get_value("Sales Taxes and Charges Template", {"company": company, "title": title})
	return sorted(
		(frappe.db.get_value("Account", row.account_head, "account_name"), row.rate)
		for row in frappe.get_doc("Sales Taxes and Charges Template", template).taxes
	)


class TestBillingSetup(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()

	def test_a_firm_sets_up_its_own_company_to_bill_from_once(self):
		with self.change_settings(SETTINGS, account_type="CA/CS Firm", billing_company=None):
			state = set_up_billing(DETAILS, name=FIRM)
			company = state["company"]
			# The GSTIN is kept as written in capitals, and says the firm is in Karnataka.
			self.assertEqual(
				(state["billing_gstin"], state["billing_state"]), ("29AAACA1234F1Z5", "Karnataka")
			)
			self.assertEqual(frappe.db.get_value("Company", company, "tax_id"), "29AAACA1234F1Z5")
			self.assertTrue(frappe.db.exists("Item", "Professional fees"))
			self.assertTrue(frappe.db.exists("Item", "Government fees (reimbursed)"))
			self.assertEqual(rates(company, WITHIN_STATE), [("Output CGST", 9), ("Output SGST", 9)])
			self.assertEqual(rates(company, OUTSIDE_STATE), [("Output IGST", 18)])
			# Setting up again keeps the company and makes nothing twice.
			again = set_up_billing({**DETAILS, "bill_prefix": "BTA2"})
			self.assertEqual(again["company"], company)
			self.assertEqual(frappe.db.count("Sales Taxes and Charges Template", {"company": company}), 2)
			self.assertEqual(billing_setup()["bill_prefix"], "BTA2")
			# The firm's company is not a client's: it stays out of everything compliance.
			self.assertNotIn(company, compliance_companies())
			self.assertNotIn(company, app_companies())
			self.assertNotIn(company, companies_overview()["not_set_up"])

	def test_billing_is_for_a_firms_managers_and_takes_only_its_details(self):
		with self.change_settings(SETTINGS, account_type="Organisation"):
			with self.assertRaisesRegex(frappe.PermissionError, "CA/CS firms"):
				billing_setup()
		with self.change_settings(SETTINGS, account_type="CA/CS Firm"):
			with self.set_user(HOLDER), self.assertRaisesRegex(frappe.PermissionError, "Compliance Manager"):
				billing_setup()
			with self.assertRaisesRegex(frappe.ValidationError, "firm's name"):
				with self.change_settings(SETTINGS, billing_company=None):
					set_up_billing(DETAILS)

	def test_a_gstin_says_its_state_and_a_wrong_one_is_refused(self):
		self.assertEqual(state_of("27AAACA1234F1Z5"), "Maharashtra")
		self.assertEqual(state_of("", "Goa"), "Goa")
		with self.assertRaisesRegex(frappe.ValidationError, "GSTIN pattern"):
			state_of("29ABC")


class TestFees(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()

	def test_filed_returns_not_yet_billed_are_priced_for_the_client(self):
		with self.change_settings(SETTINGS, account_type="CA/CS Firm"):
			save_return_fees(
				[
					{"obligation_template": "GSTR-3B (Monthly)", "amount": 1500},
					{"obligation_template": "GSTR-1 (Monthly)", "amount": 1000},
				]
			)
			sunrise = client("Billing Fee Client")
			sunrise.append("return_fees", {"obligation_template": "GSTR-1 (Monthly)", "amount": 800})
			sunrise.save()
			profile(TEST_COMPANY, sunrise.name)
			filed = filing("GSTR-3B (Monthly)", "2026-09-30", "2026-10-20", status="Filed")
			late = filing("GSTR-1 (Monthly)", "2026-09-30", "2026-10-11", status="Filed Late")
			filing("GSTR-3B (Monthly)", "2026-10-31", "2026-11-20")  # still open: not billed
			billed = filing("GSTR-1 (Monthly)", "2026-08-31", "2026-09-11", status="Filed")
			frappe.db.set_value("Compliance Task", billed, "billed_in", "ACC-SINV-TEST")
			fees = client_fees(sunrise.name)
		by_name = {row.name: row.fee for row in fees["unbilled"]}
		# The firm's price, and the client's own where it has one; a billed filing is left out.
		self.assertEqual(by_name, {filed: 1500, late: 800})
		self.assertEqual(fees["unbilled_total"], 2300)

	def test_a_fixed_fee_says_how_often_and_from_when_and_a_return_is_priced_once(self):
		with self.assertRaisesRegex(frappe.ValidationError, "give Billed, Billed From"):
			client("Billing Fee Client", fixed_fee=5000)
		plan = client("Billing Fee Client", fixed_fee=5000, fee_frequency="Monthly", fee_from="2026-04-01")
		self.assertEqual((plan.fee_frequency, str(plan.fee_from)), ("Monthly", "2026-04-01"))
		cleared = client("Billing Fee Client", fixed_fee=0, fee_frequency="Monthly", fee_from="2026-04-01")
		self.assertEqual((cleared.fee_frequency, cleared.fee_from), (None, None))
		with self.change_settings(SETTINGS, account_type="CA/CS Firm"):
			with self.assertRaisesRegex(frappe.ValidationError, "already has a price"):
				save_return_fees(
					[
						{"obligation_template": "GSTR-3B (Monthly)", "amount": 1500},
						{"obligation_template": "GSTR-3B (Monthly)", "amount": 900},
					]
				)
			with self.assertRaisesRegex(frappe.ValidationError, "a return and its fee"):
				save_return_fees([{"obligation_template": "GSTR-3B (Monthly)", "amount": 1, "status": "x"}])


class TestBills(IntegrationTestCase):
	"""A firm in Karnataka billing a client in Karnataka (CGST and SGST) or elsewhere (IGST)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		frappe.db.set_single_value(SETTINGS, {"account_type": "CA/CS Firm", "billing_company": None})
		frappe.clear_document_cache(SETTINGS, SETTINGS)
		set_up_billing({**DETAILS, "bill_prefix": "TBA"}, name="Bills Test Associates")
		save_return_fees([{"obligation_template": "GSTR-3B (Monthly)", "amount": 1500}])

	def setUp(self):
		profile(TEST_COMPANY)  # let go of the client an earlier test made, so it can be made again
		self.client = client(
			"Billing Bill Client",
			gstin="29AABCS1234Q1Z3",
			billing_email="accounts@billclient.example.com",
			fixed_fee=5000,
			fee_frequency="Monthly",
			fee_from="2026-04-01",
		).name
		profile(TEST_COMPANY, self.client)
		self.filed = filing("GSTR-3B (Monthly)", "2026-09-30", "2026-10-20", status="Filed")

	def test_a_bill_charges_gst_on_fees_and_none_on_government_fees(self):
		options = bill_options(self.client)
		self.assertIn(self.filed, [row.name for row in options["filings"]])
		self.assertEqual(options["fixed_fee"], 5000)
		name = create_bill(
			self.client,
			filings=[self.filed],
			fixed_fee=True,
			lines=[
				{"description": "Advisory on GST notice", "amount": 1000},
				{"description": "ROC filing fee paid", "amount": 500, "government": True},
			],
		)["name"]
		shown = bill(name)
		self.assertTrue(name.startswith("TBA/"))
		self.assertEqual(shown["docstatus"], 0)
		self.assertEqual(shown["net_total"], 8000)
		# GST within Karnataka on the 7,500 of fees; the government fee carries none.
		self.assertEqual(sorted(row["description"] for row in shown["taxes"]), ["Output CGST", "Output SGST"])
		self.assertEqual(shown["total_taxes_and_charges"], 1350)
		self.assertEqual(shown["grand_total"], 9350)
		# A filing on a draft is not offered for another bill.
		self.assertNotIn(self.filed, [row.name for row in bill_options(self.client)["filings"]])

	def test_sending_bills_the_filings_once_and_cancelling_frees_them(self):
		name = create_bill(self.client, filings=[self.filed])["name"]
		sent = send_bill(name)
		self.assertEqual(frappe.db.get_value("Sales Invoice", name, "docstatus"), 1)
		self.assertIsNone(sent["emailed_to"])  # no email account on the test site
		self.assertEqual(frappe.db.get_value("Compliance Task", self.filed, "billed_in"), name)
		with self.assertRaisesRegex(frappe.ValidationError, "cannot be billed"):
			create_bill(self.client, filings=[self.filed])
		cancel_bill(name)
		self.assertEqual(frappe.db.get_value("Sales Invoice", name, "docstatus"), 2)
		self.assertIsNone(frappe.db.get_value("Compliance Task", self.filed, "billed_in"))

	def test_a_client_outside_the_firms_state_pays_igst(self):
		frappe.db.set_value("Compliance Client", self.client, {"gstin": None, "billing_state": "Maharashtra"})
		name = create_bill(self.client, lines=[{"description": "Advisory", "amount": 1000}])["name"]
		shown = bill(name)
		self.assertEqual([row["description"] for row in shown["taxes"]], ["Output IGST"])
		self.assertEqual(shown["total_taxes_and_charges"], 180)

	def test_each_month_brings_one_draft_per_client_with_something_to_bill(self):
		with patch("frappe.db.commit"), patch("frappe.db.rollback"):
			make_monthly_drafts(frappe.utils.getdate("2026-11-01"))
			make_monthly_drafts(frappe.utils.getdate("2026-11-01"))
		drafts = frappe.get_all(
			"Sales Invoice",
			filters={"compliance_client": self.client, "docstatus": 0, "kx_billing_key": ("is", "set")},
			fields=["name", "kx_billing_key"],
		)
		self.assertEqual([row.kx_billing_key for row in drafts], [f"{self.client}|2026-11"])
		descriptions = [row["description"] for row in bill(drafts[0].name)["items"]]
		self.assertIn("Fixed fee, Nov 2026", descriptions)
		self.assertTrue(any(text.startswith("GSTR-3B (Monthly)") for text in descriptions))

	def test_bills_are_made_by_those_erpnext_lets_make_invoices(self):
		for user in (HOLDER, MANAGER):
			with self.set_user(user), self.assertRaisesRegex(frappe.PermissionError, "Accounts User role"):
				create_bill(self.client, filings=[self.filed])
		make_user(ACCOUNTS, ("Accounts User",))
		with self.set_user(ACCOUNTS):
			name = create_bill(self.client, filings=[self.filed])["name"]
			self.assertEqual(bill(name)["compliance_client"], self.client)
		other = frappe.get_all(
			"Sales Invoice", filters={"compliance_client": ("is", "not set")}, pluck="name", limit=1
		)
		if other:
			with self.assertRaisesRegex(frappe.PermissionError, "not one of the firm's bills"):
				bill(other[0])
