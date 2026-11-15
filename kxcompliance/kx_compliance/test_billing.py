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
	bills,
	cancel_bill,
	cancel_payment,
	client_billing,
	client_fees,
	create_bill,
	own_bill,
	receipt_pdf,
	record_payment,
	send_bill,
	set_up_billing,
)
from kxcompliance.kx_compliance.billing import (
	BILL_FORMAT,
	OUTSIDE_STATE,
	WITHIN_STATE,
	ageing_bucket,
	bill_print,
	make_monthly_drafts,
	state_of,
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
		with self.assertRaisesRegex(frappe.ValidationError, "recurring charges start from"):
			client("Billing Fee Client")
		self.assertTrue(client("Billing Fee Client", billing_from="2026-04-01").name)

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
		self.assertEqual(months[0].received + months[0].still_due, months[0].total)
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
