# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""A CA/CS firm billing its clients (RK, 15 Nov 2026), through ERPNext's own invoices and payments.

On a firm's site ERPNext's companies are the clients' companies, so the firm is set up as one more
company, the seller on every bill, and kept out of everything compliance. The app makes what
billing needs on it once: the items billed, and GST within and outside the firm's state.
"""

import frappe
from frappe import _

from kxcompliance.kx_compliance.onboarding import make_company
from kxcompliance.kx_compliance.register import get_settings, is_approver
from kxcompliance.kx_compliance.setup_import import GST_STATE_CODES, GSTIN_PATTERN

FIRM = "CA/CS Firm"
SETTINGS = "KX Compliance Settings"
FEES_ITEM = "Professional fees"
GOVERNMENT_FEES_ITEM = "Government fees (reimbursed)"
# The firm's output GST, and the two templates a bill uses: within the firm's state, or outside it.
TAX_ACCOUNTS = ("Output CGST", "Output SGST", "Output IGST")
WITHIN_STATE = "GST within state"
OUTSIDE_STATE = "GST outside state"
GST_RATE = 18
# What the firm sets about itself for its bills, from Settings → Billing.
FIRM_FIELDS = ("billing_gstin", "billing_state", "billing_address", "bank_details", "bill_prefix")


def check_firm_manager():
	if get_settings().account_type != FIRM:
		frappe.throw(_("Billing clients is for CA/CS firms."), frappe.PermissionError)
	if not is_approver():
		frappe.throw(_("Only a Compliance Manager can set billing up."), frappe.PermissionError)


def state_of(gstin: str | None, state: str | None = None) -> str | None:
	"""The state a GSTIN belongs to, or the state given when there is no GSTIN; throws on a GSTIN
	that is not one."""
	gstin = (gstin or "").strip().upper()
	if not gstin:
		return state or None
	if not GSTIN_PATTERN.match(gstin):
		frappe.throw(_("GSTIN {0} is not 15 characters in the GSTIN pattern.").format(gstin))
	found = GST_STATE_CODES.get(gstin[:2])
	if not found:
		frappe.throw(_("GSTIN {0} starts with {1}, which is not a state code.").format(gstin, gstin[:2]))
	return found


def setup_state() -> dict:
	"""Whether billing is set up, and the firm's details for its bills."""
	settings = get_settings()
	states = settings.meta.get_field("billing_state").options or ""
	return {
		"company": settings.billing_company,
		**{field: settings.get(field) or "" for field in FIRM_FIELDS},
		"states": [state for state in states.split("\n") if state],
		"can_create_company": bool(frappe.has_permission("Company", "create")) and frappe.is_setup_complete(),
	}


def set_up_firm(name: str, details: dict) -> dict:
	"""Make the firm's own company and what billing needs on it, once; then keep its details."""
	check_firm_manager()
	settings = frappe.get_doc(SETTINGS)
	if not settings.billing_company:
		company = make_company(name)
		settings.billing_company = company
	save_details(settings, details)
	make_masters(settings.billing_company)
	return setup_state()


def save_details(settings, details: dict):
	"""The firm's GSTIN, state, address, bank details and bill prefix; nothing else is taken."""
	not_allowed = sorted(set(details) - set(FIRM_FIELDS))
	if not_allowed:
		frappe.throw(_("Billing cannot set {0}.").format(", ".join(not_allowed)), frappe.PermissionError)
	for field in FIRM_FIELDS:
		if field in details:
			value = details[field]
			if not isinstance(value, str | type(None)):
				frappe.throw(_("{0} must be a single value.").format(_(settings.meta.get_label(field))))
			settings.set(field, (value or "").strip() or None)
	settings.billing_gstin = (settings.billing_gstin or "").upper() or None
	settings.billing_state = state_of(settings.billing_gstin, settings.billing_state)
	if not settings.billing_state:
		frappe.throw(_("Give the firm's GSTIN, or its state, so bills charge the right GST."))
	settings.save()
	if settings.billing_gstin:
		# ERPNext prints the company's Tax ID on its invoices; managers may not edit companies in
		# the Desk, and this is the only field the app keeps there.
		frappe.db.set_value("Company", settings.billing_company, "tax_id", settings.billing_gstin)


def make_masters(company: str):
	"""The items billed, the firm's output-tax accounts and its two GST templates; each made
	only if it is not there, so setting up again changes nothing."""
	make_item(FEES_ITEM, _("Fees for professional services"))
	make_item(GOVERNMENT_FEES_ITEM, _("Government fees paid for the client, passed on without GST"))
	accounts = {name: tax_account(company, name) for name in TAX_ACCOUNTS}
	half = GST_RATE / 2
	tax_template(company, WITHIN_STATE, [(accounts["Output CGST"], half), (accounts["Output SGST"], half)])
	tax_template(company, OUTSIDE_STATE, [(accounts["Output IGST"], GST_RATE)])


def make_item(code: str, description: str):
	if frappe.db.exists("Item", code):
		return
	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": code,
			"item_name": code,
			"description": description,
			"item_group": "Services" if frappe.db.exists("Item Group", "Services") else root("Item Group"),
			"stock_uom": "Nos",
			"is_stock_item": 0,
			"include_item_in_manufacturing": 0,
		}
	).insert()


def tax_account(company: str, account_name: str) -> str:
	existing = frappe.db.get_value("Account", {"company": company, "account_name": account_name})
	if existing:
		return existing
	parent = frappe.db.get_value(
		"Account", {"company": company, "account_name": "Duties and Taxes", "is_group": 1}
	)
	if not parent:
		frappe.throw(_("{0} has no Duties and Taxes account to keep GST under.").format(company))
	return (
		frappe.get_doc(
			{
				"doctype": "Account",
				"company": company,
				"account_name": account_name,
				"parent_account": parent,
				"account_type": "Tax",
				"tax_rate": GST_RATE / 2 if account_name != "Output IGST" else GST_RATE,
			}
		)
		.insert()
		.name
	)


def tax_template(company: str, title: str, lines: list[tuple[str, float]]) -> str:
	existing = frappe.db.get_value("Sales Taxes and Charges Template", {"company": company, "title": title})
	if existing:
		return existing
	return (
		frappe.get_doc(
			{
				"doctype": "Sales Taxes and Charges Template",
				"title": title,
				"company": company,
				"taxes": [
					{
						"charge_type": "On Net Total",
						"account_head": account,
						"description": frappe.db.get_value("Account", account, "account_name"),
						"rate": rate,
					}
					for account, rate in lines
				],
			}
		)
		.insert()
		.name
	)


def root(doctype: str) -> str:
	return frappe.db.get_value(
		doctype, {"is_group": 1, f"parent_{frappe.scrub(doctype)}": ("in", ("", None))}
	)
