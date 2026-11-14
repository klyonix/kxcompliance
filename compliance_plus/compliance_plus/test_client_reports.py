# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from compliance_plus.api import client_detail
from compliance_plus.compliance_plus.client_reports import financial_year
from compliance_plus.compliance_plus.doctype.compliance_client.test_compliance_client import (
	CLIENT_LOGIN,
	OTHER_COMPANY,
	SECOND_COMPANY,
	client,
	company,
	profile,
	task,
	with_login,
)
from compliance_plus.compliance_plus.doctype.legal_case.test_legal_case import make_case
from compliance_plus.compliance_plus.doctype.signatory.test_signatory import dsc, signatory
from compliance_plus.compliance_plus.report.client_summary.client_summary import execute as client_summary
from compliance_plus.compliance_plus.report.on_time_filing.on_time_filing import execute as on_time_filing
from compliance_plus.compliance_plus.test_utils import (
	HOLDER,
	MANAGER,
	OTHER_HOLDER,
	TEST_COMPANY,
	make_company,
	make_users,
)
from compliance_plus.install import create_standard_item_types

PERIOD = {"from_date": "2026-04-01", "to_date": "2027-03-31"}


def filing(company_name: str, status: str, **values) -> str:
	name = task(company_name)
	# The filing's own rules (proof, review) are tested elsewhere; here only the outcome counts.
	frappe.db.set_value("Compliance Task", name, {"status": status, **values})
	return name


class TestClientReports(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company()
		make_users()
		create_standard_item_types()
		company(SECOND_COMPANY, "CTSC")
		company(OTHER_COMPANY, "CTOC")

	def setUp(self):
		for doctype in (
			"Document Request",
			"Signatory",
			"Compliance Client Access",
			"Compliance Client Member",
			"Compliance Client Login",
			"Compliance Client",
		):
			frappe.db.delete(doctype)
		frappe.db.delete("Compliance Item", {"item_type": "Digital Signature Certificate"})
		frappe.db.delete("Compliance Task", {"task_key": ("like", "client-test|%")})
		frappe.db.delete("Legal Case", {"company": ("in", [TEST_COMPANY, SECOND_COMPANY])})
		for name in (TEST_COMPANY, SECOND_COMPANY, OTHER_COMPANY):
			if frappe.db.exists("Company Compliance Profile", name):
				frappe.delete_doc("Company Compliance Profile", name, force=True)
		frappe.db.delete(
			"User Permission",
			{"user": ("in", [HOLDER, OTHER_HOLDER, MANAGER, CLIENT_LOGIN]), "allow": "Company"},
		)
		# Sunrise owns two companies; Moonlight one, on another person's team.
		sunrise = with_login()
		profile(TEST_COMPANY, sunrise.name)
		profile(SECOND_COMPANY, sunrise.name)
		moonlight = client("Moonlight Traders", team=(OTHER_HOLDER,))
		profile(OTHER_COMPANY, moonlight.name)

		filing(TEST_COMPANY, "Filed")
		filing(SECOND_COMPANY, "Filed")
		filing(SECOND_COMPANY, "Filed Late", late_fee=1000, interest=150.5)
		filing(OTHER_COMPANY, "Open", is_overdue=1)
		filing(OTHER_COMPANY, "Filed")
		make_case(company=TEST_COMPANY)
		frappe.get_doc(
			{
				"doctype": "Document Request",
				"title": "Bank statement",
				"company": SECOND_COMPANY,
				"due_date": "2026-11-30",
			}
		).insert()
		dsc(signatory().name, valid_until="2026-11-20")

	def test_the_summary_counts_each_clients_year(self):
		with self.freeze_time("2026-11-15"):
			_columns, rows = client_summary(PERIOD)
		by_client = {row["client"]: row for row in rows}
		sunrise = by_client["Sunrise Group"]
		self.assertEqual(
			(sunrise["companies"], sunrise["on_time"], sunrise["late"], sunrise["overdue"]), (2, 2, 1, 0)
		)
		self.assertEqual(
			(sunrise["on_time_percent"], sunrise["late_fee"], sunrise["interest"]), (66.7, 1000, 150.5)
		)
		self.assertEqual(
			(sunrise["open_cases"], sunrise["waiting_on_client"], sunrise["dscs_expiring"]), (1, 1, 1)
		)
		# The client with an overdue filing comes first.
		self.assertEqual([row["client"] for row in rows], ["Moonlight Traders", "Sunrise Group"])
		self.assertEqual(by_client["Moonlight Traders"]["on_time_percent"], 50)

	def test_filings_outside_the_period_are_not_counted(self):
		_columns, rows = client_summary({"from_date": "2025-04-01", "to_date": "2026-03-31"})
		self.assertEqual({row["on_time"] + row["late"] for row in rows}, {0})
		self.assertEqual({row["on_time_percent"] for row in rows}, {None})

	def test_staff_see_only_their_clients(self):
		with self.set_user(HOLDER):
			_columns, rows = client_summary(PERIOD)
		self.assertEqual([row["client"] for row in rows], ["Sunrise Group"])

	def test_on_time_filing_by_client(self):
		_columns, rows = on_time_filing({**PERIOD, "group_by": "Client"})
		by_client = {row.group: row for row in rows}
		self.assertEqual((by_client["Sunrise Group"].on_time, by_client["Sunrise Group"].late), (2, 1))
		_columns, rows = on_time_filing({**PERIOD, "client": "Moonlight Traders"})
		self.assertEqual([row.group for row in rows], [OTHER_COMPANY])

	def test_the_client_page_shows_the_year(self):
		with self.set_user(CLIENT_LOGIN), self.freeze_time("2026-11-15"):
			year = client_detail("Sunrise Group")["year"]
		self.assertEqual((year["on_time"], year["late"], year["late_fee"]), (2, 1, 1000))
		self.assertEqual(year["currency"], "INR")

	def test_the_year_follows_erpnext_or_runs_april_to_march(self):
		with patch("erpnext.accounts.utils.get_fiscal_year", return_value=None):
			self.assertEqual(financial_year("2026-11-15"), ("2026-04-01", "2027-03-31"))
			self.assertEqual(financial_year("2027-02-01"), ("2026-04-01", "2027-03-31"))
