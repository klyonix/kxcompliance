# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from kxcompliance.api import (
	app_companies,
	bill,
	bill_counts,
	bill_options,
	bill_pdf,
	billing_setup,
	billing_summary,
	bills,
	cancel_bill,
	cancel_payment,
	client_billing,
	client_fees,
	client_summary,
	create_bill,
	credit_bill,
	email_receipt,
	own_bill,
	payment,
	payments,
	receipt_pdf,
	record_advance,
	record_payment,
	send_bill,
	set_up_billing,
	statement_pdf,
	write_off_bill,
)
from kxcompliance.kx_compliance.billing import (
	billing_party,
	firms_own_companies,
	BILL_FORMAT,
	OUTSIDE_STATE,
	WITHIN_STATE,
	ageing_bucket,
	bill_print,
	make_monthly_drafts,
	send_overdue_reminders,
	state_of,
	statement,
	statement_html,
)
from kxcompliance.kx_compliance.companies import companies_overview
from kxcompliance.kx_compliance.doctype.compliance_client.test_compliance_client import client, profile
from kxcompliance.kx_compliance.register import compliance_companies
from kxcompliance.kx_compliance.report.billing_by_month.billing_by_month import execute as by_month
from kxcompliance.kx_compliance.report.billing_outstanding.billing_outstanding import execute as outstanding
from kxcompliance.kx_compliance.report.unbilled_filings.unbilled_filings import execute as unbilled
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
SECOND = "Billing Second Company"


def second_company() -> str:
	if not frappe.db.exists("Company", SECOND):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": SECOND,
				"abbr": "BSCO",
				"default_currency": "INR",
				"country": "India",
			}
		).insert()
	return SECOND


def filed_for(company: str, period_end: str) -> str:
	"""A filed GSTR-3B of a company other than the test company."""
	name = (
		frappe.get_doc(
			{
				"doctype": "Compliance Task",
				"obligation_template": "GSTR-3B (Monthly)",
				"company": company,
				"period_start": period_end[:8] + "01",
				"period_end": period_end,
				"period_label": period_end[:7],
				"due_date": "2026-10-20",
				"status": "Open",
				"responsible": HOLDER,
				"task_key": f"bill-test|{company}|{frappe.generate_hash(length=6)}",
			}
		)
		.insert()
		.name
	)
	frappe.db.set_value("Compliance Task", name, "status", "Filed")
	return name


def ledger_balance(client: str) -> float:
	"""What the books say the client owes the firm: its customer's balance in the ledger."""
	from frappe.query_builder.functions import Sum

	gl = frappe.qb.DocType("GL Entry")
	customer = frappe.db.get_value("Compliance Client", client, "customer")
	return frappe.utils.flt(
		frappe.qb.from_(gl)
		.select(Sum(gl.debit - gl.credit))
		.where((gl.party_type == "Customer") & (gl.party == customer) & (gl.is_cancelled == 0))
		.run()[0][0],
		2,
	)


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

	def test_a_firm_bills_from_the_company_erpnexts_setup_made_under_its_name(self):
		own = "Billing Own Name Associates"
		if not frappe.db.exists("Company", own):
			frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": own,
					"abbr": "BONA",
					"default_currency": "INR",
					"country": "India",
				}
			).insert()
		with self.change_settings(SETTINGS, account_type="CA/CS Firm", billing_company=None):
			self.assertIn(own, firms_own_companies())
			self.assertEqual(set_up_billing(DETAILS, name=own)["company"], own)

	def test_a_clients_company_is_not_taken_as_the_firms(self):
		profile(TEST_COMPANY, client("Billing Setup Client").name)
		with self.change_settings(SETTINGS, account_type="CA/CS Firm", billing_company=None):
			self.assertNotIn(TEST_COMPANY, firms_own_companies())
			with self.assertRaisesRegex(frappe.ValidationError, "client Billing Setup Client"):
				set_up_billing(DETAILS, name=TEST_COMPANY)

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


def card(title: str, lines: list[dict], default: bool = True) -> str:
	if frappe.db.exists("Rate Card", title):
		frappe.delete_doc("Rate Card", title, force=True)
	return (
		frappe.get_doc({"doctype": "Rate Card", "title": title, "is_default": int(default), "lines": lines})
		.insert()
		.name
	)


def per_filing(template: str, amount: float, sac: str | None = None) -> dict:
	return {
		"kind": "Return",
		"obligation_template": template,
		"unit": "Per filing",
		"amount": amount,
		"sac_code": sac,
	}


def service(name: str, unit: str, amount: float, sac: str | None = None) -> dict:
	return {"kind": "Service", "service": name, "unit": unit, "amount": amount, "sac_code": sac}


class TestRates(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()

	def setUp(self):
		profile(TEST_COMPANY)

	def test_a_filing_is_priced_by_the_clients_own_rate_else_its_card_else_the_default(self):
		card(
			"Billing Standard", [per_filing("GSTR-3B (Monthly)", 1500), per_filing("GSTR-1 (Monthly)", 1000)]
		)
		card("Billing Small", [per_filing("GSTR-3B (Monthly)", 900)], default=False)
		sunrise = client("Billing Fee Client", rate_card="Billing Small")
		sunrise.append("own_rates", per_filing("GSTR-1 (Monthly)", 800, "998231"))
		sunrise.save()
		profile(TEST_COMPANY, sunrise.name)
		filed = filing("GSTR-3B (Monthly)", "2026-09-30", "2026-10-20", status="Filed")
		late = filing("GSTR-1 (Monthly)", "2026-09-30", "2026-10-11", status="Filed Late")
		filing("GSTR-3B (Monthly)", "2026-10-31", "2026-11-20")  # still open: not billed
		billed = filing("GSTR-1 (Monthly)", "2026-08-31", "2026-09-11", status="Filed")
		frappe.db.set_value("Compliance Task", billed, "billed_in", "ACC-SINV-TEST")
		with self.change_settings(SETTINGS, account_type="CA/CS Firm"):
			fees = client_fees(sunrise.name)
		# Its card's price for GSTR-3B, its own for GSTR-1; a billed filing is left out.
		self.assertEqual(
			{row.name: (row.fee, row.sac_code) for row in fees["unbilled"]},
			{filed: (900, None), late: (800, "998231")},
		)
		self.assertEqual(fees["unbilled_total"], 1700)
		# With no card of its own, the default card prices it.
		sunrise.rate_card = None
		sunrise.save()
		with self.change_settings(SETTINGS, account_type="CA/CS Firm"):
			self.assertEqual({row.fee for row in client_fees(sunrise.name)["unbilled"]}, {1500, 800})

	def test_a_rate_prices_a_return_per_filing_or_a_named_service_once(self):
		bad = (
			([{"kind": "Return", "unit": "Per filing", "amount": 1}], "choose the return"),
			([per_filing("GSTR-1 (Monthly)", 1) | {"unit": "Per month"}], "charged per filing"),
			([service("", "Per hour", 1)], "name the service"),
			([service("Advisory", "Per filing", 1)], "per hour, item, month"),
			([service("Advisory", "Per hour", 1), service("Advisory", "Per item", 2)], "already has a rate"),
		)
		for lines, message in bad:
			with self.assertRaisesRegex(frappe.ValidationError, message):
				card("Billing Bad", lines)
		first = card("Billing One", [per_filing("GSTR-1 (Monthly)", 1)])
		second = card("Billing Two", [per_filing("GSTR-1 (Monthly)", 2)])
		self.assertEqual(frappe.db.get_value("Rate Card", first, "is_default"), 0)
		self.assertEqual(frappe.db.get_value("Rate Card", second, "is_default"), 1)

	def test_a_recurring_charge_needs_the_date_it_is_billed_from(self):
		card("Billing Retainer", [service("Retainer", "Per month", 5000)])
		# A recurring line on the default card stops no client from being saved...
		self.assertTrue(client("Billing Fee Client").name)
		# ...but one on the card chosen for a client, or its own rates, needs the start date.
		with self.assertRaisesRegex(frappe.ValidationError, "recurring charges start from"):
			client("Billing Fee Client", rate_card="Billing Retainer")
		with self.assertRaisesRegex(frappe.ValidationError, "recurring charges start from"):
			client("Billing Fee Client", own_rates=[service("Retainer", "Per month", 4000)])
		self.assertTrue(
			client("Billing Fee Client", rate_card="Billing Retainer", billing_from="2026-04-01").name
		)

	def test_old_prices_and_fixed_fees_move_onto_rate_cards(self):
		from kxcompliance.patches.v1_0.move_prices_to_rate_cards import execute as move_prices

		frappe.db.delete("Rate Card")
		moved = client("Billing Moved Client").name
		fee = frappe.qb.DocType("Return Fee")
		for parenttype, parent, amount in (
			("KX Compliance Settings", "KX Compliance Settings", 1500),
			("Compliance Client", moved, 800),
		):
			frappe.qb.into(fee).columns(
				"name", "parent", "parenttype", "parentfield", "idx", "obligation_template", "amount"
			).insert(
				frappe.generate_hash(length=10),
				parent,
				parenttype,
				"return_fees",
				1,
				"GSTR-3B (Monthly)",
				amount,
			).run()
		table = frappe.qb.DocType("Compliance Client")
		frappe.qb.update(table).set(table.fixed_fee, 5000).set(table.fee_frequency, "Quarterly").set(
			table.fee_from, "2026-04-01"
		).where(table.name == moved).run()
		move_prices()
		move_prices()  # again: nothing twice
		standard = frappe.get_doc("Rate Card", {"is_default": 1})
		self.assertEqual(
			[(row.obligation_template, row.amount) for row in standard.lines], [("GSTR-3B (Monthly)", 1500)]
		)
		self.assertEqual(frappe.db.count("Rate Card"), 1)
		doc = frappe.get_doc("Compliance Client", moved)
		self.assertEqual(
			sorted(
				(row.kind, row.obligation_template or row.service, row.unit, row.amount)
				for row in doc.own_rates
			),
			[
				("Return", "GSTR-3B (Monthly)", "Per filing", 800),
				("Service", "Fixed fee", "Per quarter", 5000),
			],
		)
		self.assertEqual(str(doc.billing_from), "2026-04-01")


class TestBills(IntegrationTestCase):
	"""A firm in Karnataka billing a client in Karnataka (CGST and SGST) or elsewhere (IGST)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		frappe.db.set_single_value(SETTINGS, {"account_type": "CA/CS Firm", "billing_company": None})
		frappe.clear_document_cache(SETTINGS, SETTINGS)
		set_up_billing(
			{**DETAILS, "bill_prefix": "TBA", "default_sac": "998221"}, name="Bills Test Associates"
		)
		card(
			"Billing Standard",
			[
				per_filing("GSTR-3B (Monthly)", 1500, "998231"),
				service("Fixed fee", "Per month", 5000),
				service("Advisory", "Per hour", 2000),
			],
		)

	def setUp(self):
		profile(TEST_COMPANY)  # let go of the client an earlier test made, so it can be made again
		self.client = client(
			"Billing Bill Client",
			gstin="29AABCS1234Q1Z3",
			billing_email="accounts@billclient.example.com",
			billing_from="2026-04-01",
		).name
		profile(TEST_COMPANY, self.client)
		self.filed = filing("GSTR-3B (Monthly)", "2026-09-30", "2026-10-20", status="Filed")
		# Bills stay until the class ends; an earlier test's month bill must not count as this one's.
		invoice = frappe.qb.DocType("Sales Invoice")
		(
			frappe.qb.update(invoice)
			.set(invoice.kx_billing_key, None)
			.where(invoice.compliance_client == self.client)
		).run()

	def test_a_bill_charges_gst_on_fees_and_none_on_government_fees(self):
		options = bill_options(self.client)
		self.assertIn(self.filed, [row.name for row in options["filings"]])
		self.assertEqual([row["amount"] for row in options["recurring"]], [5000])
		self.assertEqual([row["service"] for row in options["services"]], ["Advisory"])
		name = create_bill(
			self.client,
			filings=[self.filed],
			recurring=True,
			lines=[
				{"description": "Advisory on GST notice", "amount": 1000},
				{"description": "ROC filing fee paid", "amount": 500, "government": True},
			],
		)["name"]
		shown = bill(name)
		self.assertTrue(name.startswith("TBA/"))
		self.assertEqual(shown["docstatus"], 0)
		self.assertEqual(shown["net_total"], 8000)
		# The filing's line names it once; the page links its number beside it.
		filed_line = next(row for row in shown["items"] if row["filing"] == self.filed)
		self.assertNotIn(self.filed, filed_line["description"])
		self.assertTrue(filed_line["description"].startswith("GSTR-3B (Monthly), "))
		# GST within Karnataka on the 7,500 of fees; the government fee carries none.
		self.assertEqual(sorted(row["description"] for row in shown["taxes"]), ["Output CGST", "Output SGST"])
		self.assertEqual(shown["total_taxes_and_charges"], 1350)
		self.assertEqual(shown["grand_total"], 9350)
		# A typed fee carries the firm's SAC code; a government fee none.
		sac = dict(
			frappe.get_all(
				"Sales Invoice Item",
				filters={"parent": name},
				fields=["description", "sac_code"],
				as_list=True,
			)
		)
		self.assertEqual((sac["Advisory on GST notice"], sac["ROC filing fee paid"]), ("998221", None))
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

	def test_a_bill_is_paid_in_parts_with_tds_and_a_payment_can_be_undone(self):
		name = create_bill(self.client, lines=[{"description": "Advisory", "amount": 10000}])["name"]
		send_bill(name)
		self.assertEqual(bill(name)["outstanding_amount"], 11800)  # 10,000 and 18% GST
		first = record_payment(name, 5000, "2026-11-10", "Bank Transfer", reference="UTR123", tds=1000)[
			"payment"
		]
		shown = bill(name)
		self.assertEqual(shown["outstanding_amount"], 5800)
		self.assertEqual(
			[(row["mode_of_payment"], row["paid_amount"], row["tds"]) for row in shown["payments"]],
			[("Bank Transfer", 5000, 1000)],
		)
		with self.assertRaisesRegex(frappe.ValidationError, "more than the"):
			record_payment(name, 6000, "2026-11-11", "Cash")
		with self.assertRaisesRegex(frappe.ValidationError, "after today"):
			record_payment(name, 100, "2999-01-01", "Cash")
		with self.assertRaisesRegex(frappe.ValidationError, "Pay by one of"):
			record_payment(name, 100, "2026-11-11", "Barter")
		record_payment(name, 5800, "2026-11-12", "UPI")
		self.assertEqual(bill(name)["outstanding_amount"], 0)
		cancel_payment(first)
		self.assertEqual(bill(name)["outstanding_amount"], 6000)

	def test_the_billing_list_counts_each_tab_and_what_is_due(self):
		draft = create_bill(self.client, lines=[{"description": "Draft advisory", "amount": 1000}])["name"]
		sent = create_bill(self.client, lines=[{"description": "Sent advisory", "amount": 2000}])["name"]
		send_bill(sent)
		counts = bill_counts(client=self.client)
		drafts = bills("drafts", client=self.client, page_length=100)
		self.assertIn(draft, [row.name for row in drafts["rows"]])
		self.assertEqual(counts["drafts"]["count"], drafts["total"])
		unpaid = bills("unpaid", client=self.client)
		self.assertIn(sent, [row.name for row in unpaid["rows"]])
		self.assertNotIn(draft, [row.name for row in unpaid["rows"]])
		self.assertEqual(unpaid["total"], counts["unpaid"]["count"])
		self.assertEqual(counts["unpaid"]["due"], sum(row.outstanding_amount for row in unpaid["rows"]))
		self.assertEqual([row.name for row in bills("all", text=sent)["rows"]], [sent])
		with self.assertRaisesRegex(frappe.ValidationError, "not a list of bills"):
			bills("cancelled-and-hidden")

	def test_a_client_sees_only_the_bills_sent_to_it(self):
		draft = create_bill(self.client, lines=[{"description": "Draft advisory", "amount": 1000}])["name"]
		sent = create_bill(self.client, lines=[{"description": "Sent advisory", "amount": 2000}])["name"]
		send_bill(sent)
		firm = client_billing(self.client)
		self.assertTrue({draft, sent} <= {row.name for row in firm["bills"]})
		self.assertIn("unbilled_total", firm)
		with (
			patch("kxcompliance.api.is_client_login", return_value=True),
			patch("kxcompliance.api.client_of_login", return_value=self.client),
		):
			own = client_billing(self.client)
			self.assertIn(sent, [row.name for row in own["bills"]])
			self.assertNotIn(draft, [row.name for row in own["bills"]])
			self.assertNotIn("unbilled_total", own)
			self.assertGreaterEqual(own["outstanding"], 2360)
			self.assertEqual(own_bill(sent).name, sent)
			bill_pdf(sent)
			self.assertEqual(frappe.local.response.type, "pdf")
			self.assertTrue(frappe.local.response.filecontent.startswith(b"%PDF"))
			# Printing past the invoice's permissions is for that one bill, then off again.
			self.assertFalse(frappe.flags.ignore_print_permissions)
			with self.assertRaisesRegex(frappe.PermissionError, "only bills sent to you"):
				own_bill(draft)
			with self.assertRaisesRegex(frappe.PermissionError, "only your own bills"):
				client_billing("Someone Else")

	def test_the_reports_age_what_is_due_count_each_month_and_list_what_is_unbilled(self):
		name = create_bill(self.client, lines=[{"description": "Advisory", "amount": 1000}])["name"]
		send_bill(name)
		frappe.db.set_value(
			"Sales Invoice", name, "due_date", frappe.utils.add_days(frappe.utils.nowdate(), -45)
		)
		_columns, rows = outstanding({"client": self.client})
		self.assertEqual(len(rows), 1)
		self.assertGreaterEqual(rows[0]["late_60"], 1180)
		self.assertEqual(
			rows[0]["outstanding"],
			sum(rows[0][key] for key in ("not_due", "late_30", "late_60", "late_90", "late_more")),
		)
		today = frappe.utils.getdate(frappe.utils.nowdate())
		_columns, months = by_month(
			{"from_date": today.replace(day=1), "to_date": today, "client": self.client}
		)
		self.assertEqual(len(months), 1)
		self.assertGreaterEqual(months[0].bills, 1)
		self.assertEqual(months[0].settled + months[0].still_due, months[0].total)
		_columns, waiting = unbilled({"client": self.client})
		self.assertIn(self.filed, [row.name for row in waiting])
		self.assertEqual({row.client for row in waiting}, {self.client})

	def test_a_bill_ages_by_days_past_its_due_date(self):
		today = "2026-11-30"
		self.assertEqual(ageing_bucket("2026-12-05", today), "not_due")
		self.assertEqual(ageing_bucket("2026-11-30", today), "not_due")
		self.assertEqual(ageing_bucket("2026-11-29", today), "late_30")
		self.assertEqual(ageing_bucket("2026-10-31", today), "late_30")
		self.assertEqual(ageing_bucket("2026-10-30", today), "late_60")
		self.assertEqual(ageing_bucket("2026-09-01", today), "late_90")
		self.assertEqual(ageing_bucket("2025-01-01", today), "late_more")

	def test_a_firm_not_registered_or_under_composition_charges_no_gst(self):
		registered = {**DETAILS, "bill_prefix": "TBA", "gst_status": "Registered"}
		self.addCleanup(set_up_billing, registered)
		set_up_billing(
			{**DETAILS, "gst_status": "Not registered", "billing_gstin": "", "billing_state": "Karnataka"}
		)
		self.assertFalse(frappe.db.get_single_value(SETTINGS, "billing_gstin"))
		plain = bill(create_bill(self.client, lines=[{"description": "Advisory", "amount": 1000}])["name"])
		self.assertEqual((plain["taxes"], plain["grand_total"]), ([], 1000))
		with self.assertRaisesRegex(frappe.ValidationError, "composition has a GSTIN"):
			set_up_billing({**DETAILS, "gst_status": "Composition", "billing_gstin": ""})
		set_up_billing({**DETAILS, "gst_status": "Composition"})
		supply = bill(create_bill(self.client, lines=[{"description": "Advisory", "amount": 1000}])["name"])
		self.assertEqual(supply["taxes"], [])
		with self.assertRaisesRegex(frappe.ValidationError, "GST status is one of"):
			set_up_billing({**DETAILS, "gst_status": "Exempt"})

	def test_the_firms_logo_is_public_and_goes_on_its_company(self):
		self.addCleanup(set_up_billing, {**DETAILS, "bill_prefix": "TBA", "billing_logo": ""})
		with self.assertRaisesRegex(frappe.ValidationError, "public file"):
			set_up_billing({**DETAILS, "billing_logo": "/private/files/logo.png"})
		set_up_billing({**DETAILS, "billing_logo": "/files/firm-logo.png"})
		company = frappe.db.get_single_value(SETTINGS, "billing_company")
		self.assertEqual(frappe.db.get_value("Company", company, "company_logo"), "/files/firm-logo.png")

	def test_services_are_billed_by_the_hour_and_lines_carry_their_sac_code(self):
		name = create_bill(self.client, filings=[self.filed], services=[{"service": "Advisory", "qty": 2.5}])[
			"name"
		]
		lines = frappe.get_all(
			"Sales Invoice Item",
			filters={"parent": name},
			fields=["description", "qty", "rate", "sac_code"],
			order_by="idx",
		)
		self.assertEqual(
			[(row.qty, row.rate, row.sac_code) for row in lines], [(1, 1500, "998231"), (2.5, 2000, "998221")]
		)
		self.assertTrue(lines[1].description.startswith("Advisory, 2.5"))
		with self.assertRaisesRegex(frappe.ValidationError, "not a service charged by the hour"):
			create_bill(self.client, services=[{"service": "Fixed fee", "qty": 1}])
		with self.assertRaisesRegex(frappe.ValidationError, "how many hours"):
			create_bill(self.client, services=[{"service": "Advisory", "qty": 0}])

	def test_the_bill_prints_as_a_tax_invoice_with_its_codes_words_and_a_qr_to_pay(self):
		self.addCleanup(set_up_billing, {**DETAILS, "bill_prefix": "TBA", "upi_id": ""})
		set_up_billing({**DETAILS, "bill_prefix": "TBA", "upi_id": "bills@okbank"})
		frappe.db.set_value("Compliance Client", self.client, "billing_address", "4 Lake Road, Mysuru")
		name = create_bill(self.client, filings=[self.filed])["name"]
		doc = frappe.get_doc("Sales Invoice", name)
		self.assertEqual(doc.bill_title, "Tax Invoice")
		printed = bill_print(doc)
		self.assertEqual(printed["place_of_supply"], "Karnataka (29)")
		self.assertIn("Thousand", printed["in_words"])
		self.assertTrue(printed["qr"].startswith("data:image/svg+xml;base64,"))
		html = frappe.get_print("Sales Invoice", name, doc=doc, print_format=BILL_FORMAT, no_letterhead=1)
		for expected in (
			"Tax Invoice",
			"998231",
			"29AABCS1234Q1Z3",
			"Karnataka (29)",
			"4 Lake Road",
			"bills@okbank",
			"Scan to pay",
		):
			self.assertIn(expected, html)
		bill_pdf(name)
		self.assertTrue(frappe.local.response.filecontent.startswith(b"%PDF"))

	def test_a_composition_firms_bill_is_a_bill_of_supply_and_keeps_its_title(self):
		self.addCleanup(set_up_billing, {**DETAILS, "bill_prefix": "TBA", "gst_status": "Registered"})
		set_up_billing({**DETAILS, "gst_status": "Composition"})
		name = create_bill(self.client, lines=[{"description": "Advisory", "amount": 1000}])["name"]
		set_up_billing({**DETAILS, "gst_status": "Registered"})
		doc = frappe.get_doc("Sales Invoice", name)
		printed = bill_print(doc)
		# Made under composition, it stays a bill of supply whatever the firm is now.
		self.assertEqual(printed["title"], "Bill of Supply")
		self.assertIn("Composition taxable person", printed["composition_note"])
		self.assertIsNone(printed["qr"])  # no UPI ID set

	def test_a_payment_has_a_receipt(self):
		name = create_bill(self.client, lines=[{"description": "Advisory", "amount": 1000}])["name"]
		send_bill(name)
		payment = record_payment(name, 1180, "2026-11-10", "UPI", reference="UPI-1")["payment"]
		html = frappe.get_print("Payment Entry", payment, print_format="KlyONIX Receipt", no_letterhead=1)
		for expected in ("Receipt", "UPI-1", name, "Billing Bill Client"):
			self.assertIn(expected, html)
		receipt_pdf(payment)
		self.assertTrue(frappe.local.response.filecontent.startswith(b"%PDF"))

	def test_a_credit_note_lowers_what_is_due_and_a_filing_credited_in_full_is_freed(self):
		name = create_bill(
			self.client, filings=[self.filed], lines=[{"description": "Advisory", "amount": 1000}]
		)["name"]
		send_bill(name)
		self.assertEqual(bill(name)["outstanding_amount"], 2950)  # 2,500 and GST
		advisory = bill(name)["items"][1]["name"]
		with self.assertRaisesRegex(frappe.ValidationError, "Say why"):
			credit_bill(name, "")
		with self.assertRaisesRegex(frappe.ValidationError, "Choose the line"):
			credit_bill(name, "Too vague", amount=100)
		with self.assertRaisesRegex(frappe.ValidationError, "at most its"):
			credit_bill(name, "Too much", amount=1200, line=advisory)
		part = credit_bill(name, "Advisory charged twice", amount=500, line=advisory)["credit_note"]
		self.assertTrue(part.startswith("TBA/CN/"))
		printed = bill_print(frappe.get_doc("Sales Invoice", part))
		self.assertEqual(
			(printed["title"], printed["against"]["name"], printed["qr"]), ("Credit Note", name, None)
		)
		shown = bill(name)
		self.assertEqual(shown["outstanding_amount"], 2360)  # 590 credited
		self.assertEqual([row.name for row in shown["credit_notes"]], [part])
		self.assertEqual([row["creditable"] for row in shown["items"]], [1500, 0])
		with self.assertRaisesRegex(frappe.ValidationError, "credited already"):
			credit_bill(name, "Again", amount=100, line=advisory)
		self.assertEqual(frappe.db.get_value("Compliance Task", self.filed, "billed_in"), name)

		rest = credit_bill(name, "Filed by the client itself")["credit_note"]  # every line left
		self.assertEqual(bill(name)["outstanding_amount"], 590)  # the advisory not credited
		# Its line credited in full, the filing may be billed again; undoing the credit bills it again.
		self.assertIsNone(frappe.db.get_value("Compliance Task", self.filed, "billed_in"))
		with self.assertRaisesRegex(frappe.ValidationError, "Every line"):
			credit_bill(name, "Once more")
		frappe.get_doc("Sales Invoice", rest).cancel()
		self.assertEqual(frappe.db.get_value("Compliance Task", self.filed, "billed_in"), name)

	def test_what_is_left_on_a_bill_is_written_off(self):
		name = create_bill(self.client, lines=[{"description": "Advisory", "amount": 1000}])["name"]
		send_bill(name)
		record_payment(name, 1150, "2026-11-10", "UPI")
		with self.assertRaisesRegex(frappe.ValidationError, "Say why"):
			write_off_bill(name, " ")
		write_off_bill(name, "Bank charges deducted by the client")
		shown = bill(name)
		self.assertEqual(shown["outstanding_amount"], 0)
		self.assertEqual([row.amount for row in shown["written_off"]], [30])
		with self.assertRaisesRegex(frappe.ValidationError, "nothing still due"):
			write_off_bill(name, "Again")
		with self.assertRaisesRegex(frappe.ValidationError, "still due"):
			credit_bill(name, "Settled already")

	def test_an_advance_is_used_against_the_next_bill_sent(self):
		advance = record_advance(self.client, 2000, "2026-11-01", "Bank Transfer", reference="UTR-ADV")[
			"payment"
		]
		listed = {row.name: row for row in payments(client=self.client)["rows"]}
		self.assertEqual((listed[advance].unallocated_amount, listed[advance].client), (2000, self.client))
		name = create_bill(self.client, lines=[{"description": "Advisory", "amount": 1000}])["name"]
		self.assertEqual(bill(name)["advance_held"], 2000)
		send_bill(name)
		self.assertEqual(bill(name)["outstanding_amount"], 0)  # 1,180 of the advance used
		# What the advance paid on this bill, with no TDS (not the advance's whole 2,000).
		self.assertEqual([(row["paid_amount"], row["tds"]) for row in bill(name)["payments"]], [(1180, 0)])
		self.assertEqual(frappe.db.get_value("Payment Entry", advance, "unallocated_amount"), 820)
		cancel_payment(advance)
		self.assertEqual(bill(name)["outstanding_amount"], 1180)

	def test_an_overdue_bill_is_reminded_once_at_each_step(self):
		name = create_bill(self.client, lines=[{"description": "Advisory", "amount": 1000}])["name"]
		send_bill(name)
		frappe.db.set_value("Sales Invoice", name, "due_date", "2026-11-01")
		frappe.db.set_single_value(SETTINGS, {"overdue_reminders": 1, "reminder_steps": "3, 15"})
		frappe.clear_document_cache(SETTINGS, SETTINGS)
		self.addCleanup(frappe.db.set_single_value, SETTINGS, "overdue_reminders", 0)
		with patch(
			"kxcompliance.kx_compliance.billing.email_bill", return_value="accounts@billclient.example.com"
		) as email:
			send_overdue_reminders(frappe.utils.getdate("2026-11-03"))  # 2 days late: not yet
			send_overdue_reminders(frappe.utils.getdate("2026-11-05"))  # 4 days: the 3-day step
			send_overdue_reminders(frappe.utils.getdate("2026-11-06"))  # same step: not again
			send_overdue_reminders(frappe.utils.getdate("2026-11-20"))  # 19 days: the 15-day step
		self.assertEqual([call.kwargs["overdue_days"] for call in email.call_args_list], [3, 15])
		logged = frappe.get_all("Compliance Reminder Log", filters={"sales_invoice": name}, pluck="rule_days")
		self.assertEqual(sorted(logged), [3, 15])

	def test_a_clients_year_shows_what_it_is_expected_to_pay_and_where_it_stands(self):
		filing("GSTR-3B (Monthly)", "2026-10-31", "2026-11-20", status="Cancelled")  # not expected
		before = client_summary(self.client)["activity"]  # bills earlier tests left on this client
		name = create_bill(
			self.client, filings=[self.filed], lines=[{"description": "Advisory", "amount": 1000}]
		)["name"]
		send_bill(name)  # 2,500 and GST: 2,950
		record_payment(name, 2000, frappe.utils.nowdate(), "UPI", tds=250)
		write_off_bill(name, "Settled")  # the 700 left
		summary = client_summary(self.client)
		year = summary["year"]
		# The fixed fee for each month of the year (billed from April 2026), and each return due in it.
		months = 0
		month = max(frappe.utils.getdate("2026-04-01"), frappe.utils.getdate(year["from_date"]))
		while month <= frappe.utils.getdate(year["to_date"]):
			months += 1
			month = frappe.utils.add_months(month, 1)
		self.assertEqual(
			summary["commitment"]["recurring"],
			[
				{
					"service": "Fixed fee",
					"unit": "Per month",
					"periods": months,
					"rate": 5000,
					"amount": 5000 * months,
				}
			],
		)
		due = frappe.db.count(
			"Compliance Task",
			{
				"company": TEST_COMPANY,
				"obligation_template": "GSTR-3B (Monthly)",
				"effective_due_date": ("between", [year["from_date"], year["to_date"]]),
				"status": ("not in", ("Cancelled", "Not Applicable")),
			},
		)
		filings = {row["return"]: row for row in summary["commitment"]["filings"]}
		self.assertEqual(
			(filings["GSTR-3B (Monthly)"]["count"], filings["GSTR-3B (Monthly)"]["amount"]), (due, due * 1500)
		)
		self.assertEqual(
			summary["commitment"]["total"], 5000 * months + sum(row["amount"] for row in filings.values())
		)
		self.assertEqual(
			{key: summary["activity"][key] - before[key] for key in before},
			{"billed": 2950, "credited": 0, "received": 2000, "tds": 250, "written_off": 700},
		)
		self.assertEqual(summary["rate_card"], "Billing Standard")
		with (
			patch("kxcompliance.api.is_client_login", return_value=True),
			patch("kxcompliance.api.client_of_login", return_value=self.client),
			self.assertRaisesRegex(frappe.PermissionError, "for the firm"),
		):
			client_summary(self.client)

	def test_a_statement_runs_the_balance_through_payments_tds_credits_and_write_offs(self):
		today = frappe.utils.nowdate()
		record_advance(self.client, 2000, frappe.utils.add_days(today, -5), "Bank Transfer")
		name = create_bill(self.client, lines=[{"description": "Advisory", "amount": 10000}])["name"]
		send_bill(name)  # 11,800, less the 2,000 paid ahead
		record_payment(name, 5000, today, "Bank Transfer", reference="UTR-ST", tds=1000)
		credit_bill(name, "Charged too much", amount=500, line=bill(name)["items"][0]["name"])  # 590
		write_off_bill(name, "Settled")
		shown = statement(self.client, frappe.utils.add_days(today, -3), today)
		# The advance was used against the bill, so it sits under the bill's company, before the dates.
		(section,) = shown["sections"]
		self.assertEqual((section["key"], section["opening"]), (TEST_COMPANY, -2000))
		self.assertEqual(
			[(row["kind"], row["debit"], row["credit"], row["balance"]) for row in section["rows"]],
			[
				("bill", 11800, 0, 9800),
				("payment", 0, 5000, 4800),
				("tds", 0, 1000, 3800),
				("credit", 0, 590, 3210),
				("write_off", 0, 3210, 0),
			],
		)
		self.assertEqual(section["rows"][1]["detail"], f"Received for {name}: Bank Transfer, UTR-ST")
		self.assertEqual(
			shown["summary"],
			{
				"opening": -2000,
				"billed": 11800,
				"credited": 590,
				"received": 5000,
				"tds": 1000,
				"written_off": 3210,
				"closing": 0,
			},
		)
		self.assertEqual(shown["open_bills"], [])
		self.assertEqual(shown["summary"]["closing"], ledger_balance(self.client))
		# The firm's copy says why it wrote off; the client's does not.
		self.assertEqual(section["rows"][-1]["detail"], "Written off: Settled")
		own = statement(self.client, frappe.utils.add_days(today, -3), today, own=True)
		self.assertEqual(own["sections"][0]["rows"][-1]["detail"], "Balance adjusted")
		with self.assertRaisesRegex(frappe.ValidationError, "after its end"):
			statement(self.client, today, frappe.utils.add_days(today, -1))
		# The firm and the client itself download it; another client may not.
		statement_pdf(self.client)
		self.assertTrue(frappe.local.response.filecontent.startswith(b"%PDF"))
		with (
			patch("kxcompliance.api.is_client_login", return_value=True),
			patch("kxcompliance.api.client_of_login", return_value=self.client),
		):
			statement_pdf(self.client, today, today)
			self.assertEqual(frappe.local.response.type, "pdf")
			with self.assertRaisesRegex(frappe.PermissionError, "only your own"):
				statement_pdf("Someone Else")

	def test_a_client_with_two_companies_is_billed_per_company(self):
		second = second_company()
		profile(second, self.client)
		self.addCleanup(profile, second)  # let go of it, so the next test can make the client again
		details = frappe.get_doc("Company Compliance Profile", second)
		details.billing_gstin = " 27aabcs9999q1z1 "
		details.billing_address = "Hinjewadi, Pune"
		details.save()
		self.assertEqual(
			frappe.db.get_value("Company Compliance Profile", second, ["billing_gstin", "billing_state"]),
			("27AABCS9999Q1Z1", "Maharashtra"),
		)
		other = filed_for(second, "2026-09-30")
		client_doc = frappe.get_doc("Compliance Client", self.client)
		client_doc.recurring_company = frappe.db.get_single_value(SETTINGS, "billing_company")
		with self.assertRaisesRegex(frappe.ValidationError, "not one of"):
			client_doc.save()
		client_doc = frappe.get_doc("Compliance Client", self.client)
		client_doc.recurring_company = TEST_COMPANY
		client_doc.save()

		with self.assertRaisesRegex(frappe.ValidationError, "Choose which"):
			create_bill(self.client, lines=[{"description": "Advisory", "amount": 100}])
		with self.assertRaisesRegex(frappe.ValidationError, "not one of"):
			bill_options(self.client, company=frappe.db.get_single_value(SETTINGS, "billing_company"))
		options = bill_options(self.client, company=second)
		self.assertEqual(options["companies"], sorted([TEST_COMPANY, second]))
		self.assertEqual([row.name for row in options["filings"]], [other])
		# Recurring charges go only on the bills of the company chosen to carry them.
		self.assertEqual(options["recurring"], [])
		self.assertEqual(len(bill_options(self.client, company=TEST_COMPANY)["recurring"]), 1)
		with self.assertRaisesRegex(frappe.ValidationError, "cannot be billed"):
			create_bill(self.client, filings=[self.filed], company=second)

		theirs = create_bill(self.client, filings=[other], company=second)["name"]
		shown = bill(theirs)
		# Billed to the company in Maharashtra: IGST, and its own name and GSTIN on the bill.
		self.assertEqual(
			(shown["billed_company"], [row["description"] for row in shown["taxes"]]),
			(second, ["Output IGST"]),
		)
		printed = bill_print(frappe.get_doc("Sales Invoice", theirs))["client"]
		self.assertEqual(
			(printed.client_name, printed.gstin, printed.group),
			(second, "27AABCS9999Q1Z1", "Billing Bill Client"),
		)
		send_bill(theirs)
		ours = create_bill(self.client, filings=[self.filed], company=TEST_COMPANY)["name"]
		send_bill(ours)

		# One company pays the other's bill.
		today = frappe.utils.nowdate()
		with self.assertRaisesRegex(frappe.ValidationError, "not one of"):
			record_payment(
				theirs, 100, today, "Cash", paid_by=frappe.db.get_single_value(SETTINGS, "billing_company")
			)
		paid = record_payment(theirs, 1770, today, "UPI", paid_by=TEST_COMPANY)["payment"]
		self.assertEqual(payment(paid)["paid_by_company"], TEST_COMPANY)

		shown = statement(self.client, today, today)
		closing = {section["key"]: section["closing"] for section in shown["sections"]}
		self.assertEqual(closing, {TEST_COMPANY: 1770, second: 0})
		self.assertEqual([row["name"] for row in shown["open_bills"]], [ours])
		self.assertEqual(shown["summary"]["closing"], ledger_balance(self.client))
		by_company = {row["key"]: row for row in client_summary(self.client)["by_company"]}
		self.assertEqual(
			(
				by_company[second]["billed"],
				by_company[second]["received"],
				by_company[TEST_COMPANY]["balance"],
			),
			(1770, 1770, 1770),
		)

	def test_the_billing_summary_adds_up_the_year_for_one_client_or_all(self):
		before_one = billing_summary(client=self.client)
		before_all = billing_summary()
		name = create_bill(self.client, lines=[{"description": "Advisory", "amount": 1000}])["name"]
		send_bill(name)  # 1,180
		frappe.db.set_value(
			"Sales Invoice", name, "due_date", frappe.utils.add_days(frappe.utils.nowdate(), -40)
		)
		record_payment(name, 500, frappe.utils.nowdate(), "UPI", tds=100)
		one = billing_summary(client=self.client)
		every = billing_summary()
		for after, before in ((one, before_one), (every, before_all)):
			self.assertEqual(
				{
					key: after["activity"][key] - before["activity"][key]
					for key in ("billed", "received", "tds")
				},
				{"billed": 1180, "received": 500, "tds": 100},
			)
			# 580 still due, 40 days late.
			self.assertEqual(after["ageing"]["late_60"] - before["ageing"]["late_60"], 580)
		self.assertIn(self.client, [line["client"] for line in one["owing_most"]])
		# The filing set up for the client is filed and priced, not yet billed.
		self.assertIn(self.client, [line["client"] for line in one["unbilled"]["clients"]])
		self.assertTrue(one["by_month"])
		with self.set_user(HOLDER), self.assertRaises(frappe.PermissionError):
			billing_summary()

	def test_a_payment_has_a_page_a_receipt_and_can_be_emailed(self):
		name = create_bill(self.client, lines=[{"description": "Advisory", "amount": 1000}])["name"]
		send_bill(name)
		paid = record_payment(name, 1000, frappe.utils.nowdate(), "UPI", reference="UPI-77", tds=180)[
			"payment"
		]
		shown = payment(paid)
		self.assertEqual(
			(shown["client"], shown["paid_amount"], shown["tds"], shown["reference_no"]),
			(self.client, 1000, 180, "UPI-77"),
		)
		self.assertEqual(
			[(row["name"], row["allocated"], row["still_due"]) for row in shown["bills"]], [(name, 1180, 0)]
		)
		self.assertEqual(shown["email_to"], "accounts@billclient.example.com")
		with self.assertRaisesRegex(frappe.ValidationError, "no email account"):
			with patch("kxcompliance.kx_compliance.reminders.sender_address", return_value=None):
				email_receipt(paid)
		with (
			patch("kxcompliance.kx_compliance.reminders.sender_address", return_value="firm@example.com"),
			patch("frappe.sendmail") as sendmail,
			patch("frappe.attach_print", return_value={"fname": "receipt.pdf"}),
		):
			self.assertEqual(email_receipt(paid)["emailed_to"], "accounts@billclient.example.com")
		self.assertEqual(sendmail.call_args.kwargs["recipients"], ["accounts@billclient.example.com"])
		self.assertEqual(sendmail.call_args.kwargs["reference_name"], paid)
		with self.assertRaisesRegex(frappe.DoesNotExistError, "does not exist"):
			payment("ACC-PAY-NOT-THERE")

	def test_an_advance_has_a_page_and_a_receipt(self):
		advance = record_advance(self.client, 500, frappe.utils.nowdate(), "Cash")["payment"]
		shown = payment(advance)
		self.assertEqual(
			(shown["client"], shown["bills"], shown["unallocated_amount"]), (self.client, [], 500)
		)
		receipt_pdf(advance)
		self.assertTrue(frappe.local.response.filecontent.startswith(b"%PDF"))
		with (
			patch("kxcompliance.api.is_client_login", return_value=True),
			patch("kxcompliance.api.client_of_login", return_value=self.client),
			self.assertRaisesRegex(frappe.PermissionError, "not a payment against one of your bills"),
		):
			receipt_pdf(advance)

	def test_a_months_recurring_charges_go_on_one_bill_only(self):
		month = frappe.utils.get_first_day(frappe.utils.nowdate())
		first = create_bill(self.client, recurring=True)["name"]
		self.assertTrue(any(row["description"].startswith("Fixed fee") for row in bill(first)["items"]))
		# Not offered again, refused if asked for, and the monthly draft makes no second.
		self.assertEqual(bill_options(self.client)["recurring"], [])
		with self.assertRaisesRegex(frappe.ValidationError, "already on a bill"):
			create_bill(self.client, recurring=True)
		with patch("frappe.db.commit"), patch("frappe.db.rollback"):
			make_monthly_drafts(month)
		self.assertEqual(
			frappe.db.count(
				"Sales Invoice",
				{"compliance_client": self.client, "docstatus": 0, "kx_billing_key": ("is", "set")},
			),
			1,
		)
		# Once that bill is cancelled (here, a draft deleted), the month may be billed again.
		cancel_bill(first)
		self.assertTrue(create_bill(self.client, recurring=True)["name"])

	def test_what_people_type_is_printed_as_text(self):
		frappe.db.set_value(
			"Compliance Client", self.client, "billing_address", "<img src=x onerror=alert(1)>"
		)
		name = create_bill(self.client, lines=[{"description": "<b>Advisory</b>", "amount": 1000}])["name"]
		send_bill(name)
		credit = credit_bill(name, "<script>steal()</script>")["credit_note"]
		for doc, layout in ((name, BILL_FORMAT), (credit, BILL_FORMAT)):
			html = frappe.get_print("Sales Invoice", doc, print_format=layout, no_letterhead=1)
			self.assertNotIn("<img src=x", html)
			self.assertNotIn("<script>steal", html)
			self.assertIn("&lt;img src=x", html)
		statement = statement_html(self.client, frappe.utils.nowdate(), frappe.utils.nowdate())
		self.assertNotIn("<img src=x", statement)
		self.assertIn("&lt;img src=x", statement)

	def test_staff_bill_only_the_clients_they_work_on(self):
		other = client("Billing Other Client", team=(MANAGER,)).name
		theirs = create_bill(other, lines=[{"description": "Advisory", "amount": 1000}])["name"]
		scoped = make_user("billing-scoped@example.com", ("Compliance User", "Accounts User"))
		with self.set_user(scoped):
			with self.assertRaisesRegex(frappe.PermissionError, "do not work on"):
				bill(theirs)
			with self.assertRaises(frappe.PermissionError):
				bills("all", client=other)
			self.assertNotIn(theirs, [row.name for row in bills("all", page_length=100)["rows"]])
			with self.assertRaisesRegex(frappe.PermissionError, "Choose one of your clients"):
				billing_summary()
		# Accounts staff without the app's roles bill every client, and see their accounts.
		make_user(ACCOUNTS, ("Accounts User",))
		with self.set_user(ACCOUNTS):
			self.assertEqual(bill(theirs)["name"], theirs)
			self.assertIn("commitment", client_summary(other))

	def test_a_draft_is_not_paid(self):
		name = create_bill(self.client, lines=[{"description": "Advisory", "amount": 1000}])["name"]
		with self.assertRaisesRegex(frappe.ValidationError, "Send"):
			record_payment(name, 100, "2026-11-10", "Cash")

	def test_a_client_outside_the_firms_state_pays_igst(self):
		frappe.db.set_value("Compliance Client", self.client, {"gstin": None, "billing_state": "Maharashtra"})
		name = create_bill(self.client, lines=[{"description": "Advisory", "amount": 1000}])["name"]
		shown = bill(name)
		self.assertEqual([row["description"] for row in shown["taxes"]], ["Output IGST"])
		self.assertEqual(shown["total_taxes_and_charges"], 180)

	def test_a_retainer_with_no_date_to_bill_from_is_named_not_dropped(self):
		frappe.db.set_value("Compliance Client", self.client, "billing_from", None)
		options = bill_options(self.client)
		self.assertEqual(options["recurring"], [])
		self.assertEqual(options["recurring_without_start"], ["Fixed fee"])
		self.assertEqual(client_summary(self.client)["recurring_without_start"], ["Fixed fee"])
		frappe.db.set_value("Compliance Client", self.client, "billing_from", "2026-04-01")
		self.assertEqual(bill_options(self.client)["recurring_without_start"], [])

	def test_a_company_with_only_a_gst_registration_is_billed_in_its_state(self):
		# The GSTIN was given in setup as the company's registration, not as a billing GSTIN.
		frappe.db.set_value("Compliance Client", self.client, {"gstin": None, "billing_state": None})
		company = frappe.get_doc("Company Compliance Profile", TEST_COMPANY)
		company.append(
			"registrations",
			{"registration_type": "GST", "registration_number": "29AABCK1234Q1Z3", "state": "Karnataka"},
		)
		company.save()
		name = create_bill(self.client, lines=[{"description": "Advisory", "amount": 1000}])["name"]
		shown = bill(name)
		self.assertEqual(
			[row["description"] for row in shown["taxes"]], ["Output CGST", "Output SGST"]
		)
		self.assertEqual(billing_party(self.client, TEST_COMPANY).gstin, "29AABCK1234Q1Z3")

	def test_each_month_brings_one_draft_per_client_with_something_to_bill(self):
		with patch("frappe.db.commit"), patch("frappe.db.rollback"):
			make_monthly_drafts(frappe.utils.getdate("2026-11-01"))
			make_monthly_drafts(frappe.utils.getdate("2026-11-01"))
		drafts = frappe.get_all(
			"Sales Invoice",
			filters={"compliance_client": self.client, "docstatus": 0, "kx_billing_key": ("is", "set")},
			fields=["name", "kx_billing_key"],
		)
		# One per company and month (a client's companies are billed apart).
		self.assertEqual([row.kx_billing_key for row in drafts], [f"{self.client}|{TEST_COMPANY}|2026-11"])
		descriptions = [row["description"] for row in bill(drafts[0].name)["items"]]
		self.assertTrue(any(text.startswith("Fixed fee, ") for text in descriptions))
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
