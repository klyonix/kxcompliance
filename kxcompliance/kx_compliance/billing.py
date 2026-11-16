# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""A CA/CS firm billing its clients (RK, 15 Nov 2026), through ERPNext's own invoices and payments.

On a firm's site ERPNext's companies are the clients' companies, so the firm is set up as one more
company, the seller on every bill, and kept out of everything compliance. The app makes what
billing needs on it once: the items billed, and GST within and outside the firm's state. Bills are
draft Sales Invoices made from a client's filed returns, its fixed fee and any other lines; sending
one submits it and emails it, and its filings are then billed, until the bill is cancelled.
"""

from datetime import date

import frappe
from frappe import _
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, add_months, flt, format_date, get_first_day, getdate, nowdate
from frappe.utils.caching import request_cache

from kxcompliance import scoped
from kxcompliance.kx_compliance.onboarding import make_company
from kxcompliance.kx_compliance.register import (
	client_title,
	client_titles,
	get_settings,
	is_approver,
	rate_card_title,
)
from kxcompliance.kx_compliance.setup_import import GST_STATE_CODES, GSTIN_PATTERN

FIRM = "CA/CS Firm"
SETTINGS = "KX Compliance Settings"
FEES_ITEM = "Professional fees"
GOVERNMENT_FEES_ITEM = "Government fees (reimbursed)"
# Services charged by the hour, counted in hours (Nos must be whole numbers).
HOURS_ITEM = "Professional fees (hours)"
# The firm's output GST, and the two templates a bill uses: within the firm's state, or outside it.
TAX_ACCOUNTS = ("Output CGST", "Output SGST", "Output IGST")
WITHIN_STATE = "GST within state"
OUTSIDE_STATE = "GST outside state"
GST_RATE = 18
# What the firm sets about itself for its bills, from Settings → Billing.
FIRM_FIELDS = (
	"gst_status",
	"billing_gstin",
	"billing_state",
	"billing_address",
	"bank_details",
	"upi_id",
	"bill_prefix",
	"default_sac",
	"billing_logo",
	"overdue_reminders",
	"reminder_steps",
)
# A firm registered for GST charges it on its bills; one not registered, or under composition
# (which issues a bill of supply), charges none.
REGISTERED = "Registered"
GST_STATUSES = (REGISTERED, "Not registered", "Composition")
# What a bill is called, by the firm's GST status when it is made.
BILL_TITLES = {REGISTERED: "Tax Invoice", "Not registered": "Invoice", "Composition": "Bill of Supply"}
COMPOSITION_NOTE = "Composition taxable person, not eligible to collect tax on supplies."
# The layouts the firm's bills and payment receipts are printed in (print_format/).
BILL_FORMAT = "KlyONIX Bill"
RECEIPT_FORMAT = "KlyONIX Receipt"
# A filing is billed once it is filed (compliance_task.FILED_STATUSES).
BILLABLE_STATUSES = ("Filed", "Filed Late")
WITHOUT_GST = "Without GST"
# Who may open billing in the app at all; making, sending and cancelling bills is then ERPNext's
# own right to Sales Invoices (Accounts User or Manager), which its accounting checks need too.
BILLING_ROLES = frozenset({"System Manager", "Compliance Manager", "Accounts Manager", "Accounts User"})
# A bill is due this many days after it is made.
BILL_DUE_DAYS = 15
# How a rate is charged: a return per filing; a service as it is done (per hour or item), or every
# month, quarter or year from the client's "recurring charges from" date.
PER_FILING = "Per filing"
AS_DONE = ("Per hour", "Per item")
RECURRING_MONTHS = {"Per month": 1, "Per quarter": 3, "Per year": 12}
# How clients pay, each into the firm's cash or its bank (Mode of Payment, type).
PAYMENT_MODES = {"Cash": "Cash", "Bank Transfer": "Bank", "UPI": "Bank", "Cheque": "Bank"}
TDS_ACCOUNT = "TDS Receivable"


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
	own = [] if settings.billing_company else firms_own_companies()
	return {
		"company": settings.billing_company,
		# The company ERPNext's own setup made under the firm's name, offered as the one to bill from.
		"suggested_name": own[0] if len(own) == 1 else "",
		**{field: settings.get(field) or "" for field in FIRM_FIELDS},
		"states": [state for state in states.split("\n") if state],
		"can_create_company": bool(frappe.has_permission("Company", "create")) and frappe.is_setup_complete(),
		"gst_statuses": list(GST_STATUSES),
		"settings_record": scoped.settings_record(),
	}


def firms_own_companies() -> list[str]:
	"""Companies that are no client's: the firm's own, such as the one ERPNext's setup made."""
	clients = set(
		scoped.get_all("Company Compliance Profile", filters={"client": ("is", "set")}, pluck="company")
	)
	return [
		name for name in scoped.get_all("Company", pluck="name", order_by="creation") if name not in clients
	]


def firm_company(name: str) -> str:
	"""The firm's company under this name: the existing one if it is the firm's own, else a new one."""
	if not scoped.exists("Company", name):
		return make_company(name)
	client = scoped.get_value("Company Compliance Profile", {"company": name}, "client")
	if client:
		frappe.throw(
			_("{0} is a company of the client {1}; give the firm's own name for its bills.").format(
				name, client_title(client)
			)
		)
	return name


def set_up_firm(name: str, details: dict) -> dict:
	"""Take the firm's own company, made if it is not there, and what billing needs on it, once;
	then keep its details."""
	check_firm_manager()
	settings = scoped.settings(for_update=True)
	if not settings.billing_company:
		settings.billing_company = firm_company(name)
	save_details(settings, details)
	make_masters(settings.billing_company)
	return setup_state()


def save_details(settings, details: dict):
	"""The firm's GST status, GSTIN, state, address, bank details, UPI ID, bill prefix and logo;
	nothing else is taken."""
	not_allowed = sorted(set(details) - set(FIRM_FIELDS))
	if not_allowed:
		frappe.throw(_("Billing cannot set {0}.").format(", ".join(not_allowed)), frappe.PermissionError)
	for field in FIRM_FIELDS:
		if field in details:
			value = details[field]
			if field == "overdue_reminders":
				settings.overdue_reminders = 1 if value else 0
				continue
			if not isinstance(value, str | type(None)):
				frappe.throw(_("{0} must be a single value.").format(_(settings.meta.get_label(field))))
			settings.set(field, (value or "").strip() or None)
	settings.gst_status = settings.gst_status or REGISTERED
	if settings.gst_status not in GST_STATUSES:
		frappe.throw(
			_("GST status is one of {0}, not {1}.").format(", ".join(GST_STATUSES), settings.gst_status)
		)
	settings.reminder_steps = ", ".join(str(day) for day in reminder_steps(settings.reminder_steps)) or None
	settings.billing_gstin = (settings.billing_gstin or "").upper() or None
	if settings.gst_status != "Not registered" and not settings.billing_gstin:
		frappe.throw(_("A firm that is {0} has a GSTIN; give it.").format(_(settings.gst_status).lower()))
	settings.billing_state = state_of(settings.billing_gstin, settings.billing_state)
	if not settings.billing_state:
		frappe.throw(_("Give the firm's state, which bills show as where it supplies from."))
	if settings.billing_logo and not settings.billing_logo.startswith("/files/"):
		frappe.throw(_("Attach the firm's logo as a public file, so bills can print it."))
	settings.save()
	# ERPNext prints the company's Tax ID and logo on its documents; managers may not edit companies
	# in the Desk, and these are the only fields the app keeps there.
	frappe.db.set_value(
		"Company",
		settings.billing_company,
		{"tax_id": settings.billing_gstin, "company_logo": settings.billing_logo},
	)


def make_masters(company: str):
	"""The items billed, the firm's output-tax accounts and its two GST templates; each made
	only if it is not there, so setting up again changes nothing."""
	make_item(FEES_ITEM, _("Fees for professional services"))
	make_item(GOVERNMENT_FEES_ITEM, _("Government fees paid for the client, passed on without GST"))
	make_item(HOURS_ITEM, _("Professional services charged by the hour"), uom="Hour")
	accounts = {name: tax_account(company, name) for name in TAX_ACCOUNTS}
	half = GST_RATE / 2
	tax_template(company, WITHIN_STATE, [(accounts["Output CGST"], half), (accounts["Output SGST"], half)])
	tax_template(company, OUTSIDE_STATE, [(accounts["Output IGST"], GST_RATE)])
	# Government fees passed on carry no GST: each such line on a bill takes this template, taxed at
	# nothing on every GST account (see government_fees_untaxed). The item is shared by every
	# company on the site, so the template goes on the bill's line, not on the item.
	item_tax_template(company, list(accounts.values()))
	# Payments: into cash or the firm's bank (payment_account), and TDS the client deducts, kept as
	# an asset.
	bank_ledger(company)
	for mode, kind in PAYMENT_MODES.items():
		payment_mode(mode, kind)
	ledger(company, TDS_ACCOUNT, "Tax Assets")
	# On a firm's site invoices and payments are the firm's bills and receipts: print them so.
	for doctype, layout in (("Sales Invoice", BILL_FORMAT), ("Payment Entry", RECEIPT_FORMAT)):
		make_property_setter(
			doctype,
			None,
			"default_print_format",
			layout,
			"Data",
			for_doctype=True,
			validate_fields_for_doctype=False,
		)


def ledger(company: str, name: str, parent_name: str, account_type: str | None = None) -> str:
	"""An account under one of the company's groups, made only if it is not there."""
	existing = scoped.get_value("Account", {"company": company, "account_name": name, "is_group": 0})
	if existing:
		return existing
	parent = scoped.get_value("Account", {"company": company, "account_name": parent_name, "is_group": 1})
	if not parent:
		frappe.throw(_("{0} has no {1} account to keep {2} under.").format(company, parent_name, name))
	return (
		frappe.get_doc(
			{
				"doctype": "Account",
				"company": company,
				"account_name": name,
				"parent_account": parent,
				"account_type": account_type,
			}
		)
		.insert()
		.name
	)


def bank_ledger(company: str) -> str:
	"""The company's bank account in the books: its default, else one made under Bank Accounts."""
	bank = scoped.get_value("Company", company, "default_bank_account")
	if bank:
		return bank
	bank = ledger(company, "Bank", "Bank Accounts", "Bank")
	# ERPNext keeps the company's default bank on the company; the app sets only this, once.
	frappe.db.set_value("Company", company, "default_bank_account", bank)
	return bank


def payment_mode(mode: str, kind: str):
	"""A way of paying. Modes are shared by every company on the site, so the account a payment
	goes into is the company's own (payment_account), not one kept on the mode."""
	if not scoped.exists("Mode of Payment", mode):
		frappe.get_doc({"doctype": "Mode of Payment", "mode_of_payment": mode, "type": kind}).insert()


def payment_account(company: str, mode: str) -> str | None:
	"""Where a payment by this mode goes in the company's books: its cash or its bank account."""
	field = "default_cash_account" if PAYMENT_MODES.get(mode) == "Cash" else "default_bank_account"
	return scoped.get_value("Company", company, field)


def item_tax_template(company: str, accounts: list[str]) -> str:
	existing = scoped.get_value("Item Tax Template", {"company": company, "title": WITHOUT_GST})
	if existing:
		return existing
	return (
		frappe.get_doc(
			{
				"doctype": "Item Tax Template",
				"title": WITHOUT_GST,
				"company": company,
				"taxes": [{"tax_type": account, "tax_rate": 0} for account in accounts],
			}
		)
		.insert()
		.name
	)


def make_item(code: str, description: str, uom: str = "Nos"):
	if scoped.exists("Item", code):
		return
	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": code,
			"item_name": code,
			"description": description,
			"item_group": "Services" if scoped.exists("Item Group", "Services") else root("Item Group"),
			"stock_uom": uom,
			"is_stock_item": 0,
			"include_item_in_manufacturing": 0,
		}
	).insert()


def tax_account(company: str, account_name: str) -> str:
	existing = scoped.get_value("Account", {"company": company, "account_name": account_name})
	if existing:
		return existing
	parent = scoped.get_value(
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
	existing = scoped.get_value("Sales Taxes and Charges Template", {"company": company, "title": title})
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
						"description": scoped.get_value("Account", account, "account_name"),
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
	return scoped.get_value(doctype, {"is_group": 1, f"parent_{frappe.scrub(doctype)}": ("in", ("", None))})


def rate_key(line) -> tuple[str, str]:
	"""What a rate prices: a return, or a service by its name."""
	if line.get("kind") == "Return":
		return ("Return", line.get("obligation_template") or "")
	return ("Service", (line.get("service") or "").strip())


def check_rate_lines(lines, where: str):
	"""Each line prices a return per filing, or a named service by hour, item or period; and each
	return or service once."""
	seen = set()
	for row in lines:
		if row.kind == "Return":
			row.service = None
			if not row.obligation_template:
				frappe.throw(_("{0} row {1}: choose the return it prices.").format(where, row.idx))
			if row.unit != PER_FILING:
				frappe.throw(
					_("{0} row {1}: a return is charged per filing, not {2}.").format(
						where, row.idx, _(row.unit)
					)
				)
		else:
			row.obligation_template = None
			row.service = (row.service or "").strip()
			if not row.service:
				frappe.throw(_("{0} row {1}: name the service.").format(where, row.idx))
			if row.unit == PER_FILING:
				frappe.throw(
					_("{0} row {1}: {2} is charged per hour, item, month, quarter or year.").format(
						where, row.idx, row.service
					)
				)
		key = rate_key(row)
		if key in seen:
			frappe.throw(_("{0} row {1}: {2} already has a rate.").format(where, row.idx, key[1]))
		seen.add(key)


def keep_one_default(card):
	"""One default card at a time: making one the default takes it from the others."""
	if not card.is_default:
		return
	table = frappe.qb.DocType("Rate Card")
	(
		frappe.qb.update(table)
		.set(table.is_default, 0)
		.where(table.name != card.name)
		.where(scoped.where(table))
	).run()


def check_client_rates(client):
	"""A client's own rates, and a start date for any monthly, quarterly or yearly charge chosen
	for it: in its own rates or on the card picked for it. The default card is left out: a
	recurring line added there must not stop every client from being saved; a client without a
	start date is simply not charged it (recurring_due)."""
	check_rate_lines(client.own_rates, _("Own Rates"))
	if client.billing_from:
		return
	lines = list(client.own_rates)
	if client.rate_card:
		lines += scoped.get_all(
			"Rate Card Line",
			filters={"parenttype": "Rate Card", "parent": client.rate_card},
			fields=["service", "unit"],
		)
	recurring = [line for line in lines if line.get("unit") in RECURRING_MONTHS]
	if recurring:
		frappe.throw(
			_("{0} pays {1} {2}; give the date its recurring charges start from.").format(
				client.client_name, recurring[0].get("service"), _(recurring[0].get("unit")).lower()
			)
		)


def default_card() -> str | None:
	return scoped.get_value("Rate Card", {"is_default": 1})


LINE_FIELDS = ["kind", "obligation_template", "service", "unit", "amount", "sac_code"]


def rates_for(clients: list[str], unsaved: dict | None = None) -> dict[str, dict[tuple, dict]]:
	"""Each client's rates: its card's (or the default card's), with its own rates in their place.
	Read in a few queries however many clients there are. `unsaved` gives a client document being
	saved, whose card and own rates are read from it rather than the database."""
	unsaved = unsaved or {}
	saved = [name for name in clients if name not in unsaved]
	card_of = dict(
		scoped.get_all(
			"Compliance Client",
			filters={"name": ("in", saved or [""])},
			fields=["name", "rate_card"],
			as_list=True,
		)
	)
	for name, doc in unsaved.items():
		card_of[name] = doc.rate_card
	fallback = default_card()
	cards = {card_of.get(name) or fallback for name in clients} - {None}
	card_lines: dict[str, list] = {}
	for row in scoped.get_all(
		"Rate Card Line",
		filters={"parenttype": "Rate Card", "parent": ("in", list(cards) or [""])},
		fields=["parent", *LINE_FIELDS],
		order_by="idx asc",
	):
		card_lines.setdefault(row.parent, []).append(row)
	own: dict[str, list] = {}
	for row in scoped.get_all(
		"Rate Card Line",
		filters={"parenttype": "Compliance Client", "parent": ("in", saved or [""])},
		fields=["parent", *LINE_FIELDS],
		order_by="idx asc",
	):
		own.setdefault(row.parent, []).append(row)
	for name, doc in unsaved.items():
		own[name] = [{field: row.get(field) for field in LINE_FIELDS} for row in doc.own_rates]
	rates = {}
	for name in clients:
		merged = {}
		for line in [*card_lines.get(card_of.get(name) or fallback, []), *own.get(name, [])]:
			merged[rate_key(line)] = {field: line.get(field) for field in LINE_FIELDS}
		rates[name] = merged
	return rates


def unbilled_filings(client: str) -> list[dict]:
	"""The client's filings that are filed, have a fee and are on no bill yet (sent or draft),
	oldest first."""
	return unbilled_for([client])


def unbilled_for(clients: list[str]) -> list[dict]:
	"""Filed returns with a rate that are on no bill yet (sent or draft), for these clients, oldest
	first; each with its client, fee and SAC code. Read in a few queries however many clients."""
	if not clients:
		return []
	owner = dict(
		scoped.get_all(
			"Company Compliance Profile",
			filters={"client": ("in", clients)},
			fields=["company", "client"],
			as_list=True,
		)
	)
	if not owner:
		return []
	rates = rates_for(clients)
	rows = scoped.get_all(
		"Compliance Task",
		filters={
			"company": ("in", list(owner)),
			"status": ("in", BILLABLE_STATUSES),
			"billed_in": ("is", "not set"),
		},
		fields=["name", "obligation_template", "period_label", "company", "filed_on"],
		order_by="filed_on asc, name asc",
	)
	drafted = on_drafts([row.name for row in rows])
	titles = client_titles(owner.values())
	found = []
	for row in rows:
		row.client = owner[row.company]
		row.client_name = titles.get(row.client, row.client)
		rate = rates[row.client].get(("Return", row.obligation_template)) or {}
		row.fee = rate.get("amount")
		row.sac_code = rate.get("sac_code")
		if row.fee and row.name not in drafted:
			found.append(row)
	return found


def client_fees(client: str) -> dict:
	"""What a client would be billed for its filings now, the rates it pays, and its companies."""
	unbilled = unbilled_filings(client)
	return {
		"companies": client_companies(client),
		"rates": list(rates_for([client])[client].values()),
		"unbilled": unbilled,
		"unbilled_total": sum(row.fee for row in unbilled),
	}


@request_cache
def billable_clients() -> tuple[str, ...] | None:
	"""The clients this person may bill: None for any (accounts staff, and the app's people not
	kept to some clients), else those they may read. The app's people are kept to their clients
	by permissions.py; Sales Invoices carry no such rule, so billing applies it here."""
	from kxcompliance.api import APP_ROLES
	from kxcompliance.permissions import is_restricted

	user = frappe.session.user
	if not (APP_ROLES & set(frappe.get_roles(user))) or not is_restricted(user):
		return None
	return tuple(frappe.get_list("Compliance Client", pluck="name", limit=0))


def check_client_allowed(client: str | None):
	allowed = billable_clients()
	if allowed is not None and client not in allowed:
		frappe.throw(
			_("You do not work on {0}, so cannot see its bills.").format(client_title(client)),
			frappe.PermissionError,
		)


def check_biller():
	"""Bills are a firm's, made by those ERPNext lets make invoices: its Accounts Users and
	Managers. ERPNext checks the accounts a bill posts to as well, so no other way is offered."""
	if get_settings().account_type != FIRM:
		frappe.throw(_("Billing clients is for CA/CS firms."), frappe.PermissionError)
	if not get_settings().billing_company:
		frappe.throw(_("Set billing up first, in Settings → Billing."))
	if not frappe.has_permission("Sales Invoice", "create"):
		frappe.throw(
			_("Billing clients needs the Accounts User role; ask a System Manager to give it to you."),
			frappe.PermissionError,
		)


def leaf(doctype: str, preferred: tuple[str | None, ...]) -> str | None:
	"""The first of `preferred` that exists and is not a group, else any that is not."""
	for name in preferred:
		if name and scoped.exists(doctype, {"name": name, "is_group": 0}):
			return name
	return scoped.get_value(doctype, {"is_group": 0})


def customer_for(client: str) -> str:
	"""The client's Customer, made the first time it is billed. A link the app keeps, not a state
	of the client, so it is written directly."""
	values = scoped.get_value(
		"Compliance Client", client, ["client_name", "client_kind", "customer", "gstin"], as_dict=True
	)
	if not values:
		frappe.throw(_("Client {0} does not exist.").format(client))
	if values.customer and scoped.exists("Customer", values.customer):
		return values.customer
	selling = frappe.get_single("Selling Settings")
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": values.client_name,
			"customer_type": "Individual" if values.client_kind == "Individual" else "Company",
			"customer_group": leaf("Customer Group", (selling.customer_group, "Commercial")),
			"territory": leaf("Territory", (selling.territory, "India")),
			"tax_id": values.gstin,
		}
	)
	# The client's own record in the books, made by the app on its first bill, after check_biller;
	# accounts staff may make invoices without keeping the Customer list.
	customer.flags.ignore_permissions = True
	customer.insert()
	frappe.db.set_value("Compliance Client", client, "customer", customer.name, update_modified=False)
	return customer.name


def follow_client(client):
	"""A client's name or GSTIN changed: its Customer follows, so bills carry them."""
	if client.customer and (client.has_value_changed("client_name") or client.has_value_changed("gstin")):
		frappe.db.set_value(
			"Customer", client.customer, {"customer_name": client.client_name, "tax_id": client.gstin}
		)


def client_companies(client: str) -> list[str]:
	"""The client's companies, by name (a profile is named after its company)."""
	return scoped.get_all(
		"Company Compliance Profile", filters={"client": client}, pluck="name", order_by="name asc"
	)


def bill_company(client: str, company: str | None) -> str | None:
	"""The company a bill is for: the one asked, which must be the client's; else the client's only
	company. A client without companies is billed as a whole."""
	companies = client_companies(client)
	if company:
		if company not in companies:
			frappe.throw(_("{0} is not one of {1}'s companies.").format(company, client_title(client)))
		return company
	if len(companies) > 1:
		frappe.throw(_("Choose which of {0}'s companies the bill is for.").format(client_title(client)))
	return companies[0] if companies else None


def recurring_company_of(client: str, companies: list[str]) -> str | None:
	"""The company whose bills carry the client's recurring charges: the one chosen, else its first."""
	chosen = scoped.get_value("Compliance Client", client, "recurring_company")
	if chosen in companies:
		return chosen
	return companies[0] if companies else None


def billing_party(client: str | None, company: str | None = None) -> frappe._dict:
	"""Who a bill is to: the company, with its own billing details where it has them, else the
	client's. `client_name` is the name printed on the bill."""
	base = (
		scoped.get_value(
			"Compliance Client",
			client,
			[
				"client_name",
				"gstin",
				"billing_state",
				"billing_address",
				"billing_email",
				"contact_email",
				"logo",
			],
			as_dict=True,
		)
		if client
		else None
	) or frappe._dict()
	own = (
		scoped.get_value(
			"Company Compliance Profile",
			company,
			["billing_gstin", "billing_state", "billing_address", "billing_email"],
			as_dict=True,
		)
		if company
		else None
	) or frappe._dict()
	# With no billing GSTIN of its own, the company's GST registration says where it is.
	registered = frappe._dict() if own.billing_gstin else gst_registration(company)
	return frappe._dict(
		client=client,
		company=company,
		client_name=company or base.client_name,
		group=base.client_name if company else None,
		gstin=own.billing_gstin or registered.gstin or base.gstin,
		billing_state=own.billing_state or registered.state or base.billing_state,
		billing_address=own.billing_address or base.billing_address,
		email=own.billing_email or base.billing_email or base.contact_email,
		logo=base.logo,
	)


def gst_registration(company: str | None) -> frappe._dict:
	"""The company's GSTIN and its state, when it has one GST registration; with several, which
	one a bill is to is the profile's billing GSTIN to say."""
	if not company:
		return frappe._dict()
	rows = scoped.get_all(
		"Compliance Registration",
		filters={"parent": company, "parenttype": "Company Compliance Profile", "registration_type": "GST"},
		fields=["registration_number", "state"],
		limit=2,
	)
	if len(rows) != 1:
		return frappe._dict()
	gstin = (rows[0].registration_number or "").strip().upper()
	return frappe._dict(gstin=gstin or None, state=rows[0].state or GST_STATE_CODES.get(gstin[:2]))


def tax_template_for(client_state: str | None) -> str | None:
	"""Within the firm's state, CGST and SGST; elsewhere (or not known), IGST."""
	settings = get_settings()
	title = WITHIN_STATE if client_state and client_state == settings.billing_state else OUTSIDE_STATE
	return scoped.get_value(
		"Sales Taxes and Charges Template", {"company": settings.billing_company, "title": title}
	)


def series(credit: bool = False) -> str | None:
	"""The firm's bill numbering, RA/26-27/0001 (credit notes RA/CN/26-27/0001), offered on Sales
	Invoice; None without a prefix."""
	prefix = (get_settings().bill_prefix or "").strip()
	if not prefix:
		return None
	name = f"{prefix}/CN/.TFY./.####" if credit else f"{prefix}/.TFY./.####"
	options = frappe.get_meta("Sales Invoice").get_field("naming_series").options or ""
	if name not in options.split("\n"):
		make_property_setter(
			"Sales Invoice",
			"naming_series",
			"options",
			f"{options}\n{name}".strip(),
			"Text",
			validate_fields_for_doctype=False,
		)
	return name


def period_name(month: date, months: int) -> str:
	"""Nov 2026; or Nov 2026 to Jan 2027 for a quarter or a year."""
	first = format_date(month, "MMM yyyy")
	if months == 1:
		return first
	return _("{0} to {1}").format(first, format_date(add_months(month, months - 1), "MMM yyyy"))


def recurring_due(rates: dict[tuple, dict], start, month: date) -> list[dict]:
	"""The monthly, quarterly and yearly charges whose period starts in this month, counted from
	the client's `start`; each a bill line's description, rate and SAC code."""
	if not start:
		return []
	due = []
	for line in rates.values():
		months = RECURRING_MONTHS.get(line["unit"])
		if months and starts_period(start, months, month) and line["amount"]:
			due.append(
				{
					"description": _("{0}, {1}").format(line["service"], period_name(month, months)),
					"amount": line["amount"],
					"sac_code": line["sac_code"],
				}
			)
	return due


def recurring_without_start(rates: dict[tuple, dict], start) -> list[str]:
	"""The client's recurring charges, when it has no date to bill them from and so none is billed."""
	if start:
		return []
	return [
		line["service"] for line in rates.values() if RECURRING_MONTHS.get(line["unit"]) and line["amount"]
	]


def starts_period(start, months: int, month: date) -> bool:
	"""Whether a charge every `months` months, counted from `start`, has a period starting in this month."""
	first = get_first_day(start)
	gap = (month.year - first.year) * 12 + month.month - first.month
	return gap >= 0 and not gap % months


def on_drafts(filings: list[str]) -> set[str]:
	"""Of these filings, those already on a bill not yet sent, so none is put on two."""
	if not filings:
		return set()
	item = frappe.qb.DocType("Sales Invoice Item")
	invoice = frappe.qb.DocType("Sales Invoice")
	return set(
		(
			frappe.qb.from_(item)
			.join(invoice)
			.on(invoice.name == item.parent)
			.select(item.compliance_task)
			.where(item.compliance_task.isin(filings) & (invoice.docstatus == 0))
			.where(scoped.where(item))
			.where(scoped.where(invoice))
		).run(pluck=True)
	)


def make_bill(
	client: str,
	filings: list[str] | None = None,
	month: date | None = None,
	lines: list[dict] | None = None,
	key: str | None = None,
	services: list[dict] | None = None,
	company: str | None = None,
) -> str:
	"""A draft bill for one of a client's companies: the filings chosen (from that company's
	unbilled ones), the recurring charges whose period starts in `month` when this company carries
	them, services done ({service, qty}, at the client's rates), and any other lines ({description,
	amount, government})."""
	settings = get_settings()
	company = bill_company(client, company)
	unbilled = {
		row.name: row for row in unbilled_filings(client) if company is None or row.company == company
	}
	asked = filings or []
	not_offered = [name for name in asked if name not in unbilled]
	if not_offered:
		frappe.throw(
			_("{0} cannot be billed: not filed, not priced, or already on a bill.").format(
				", ".join(not_offered)
			)
		)
	items = [
		{
			"item_code": FEES_ITEM,
			# The filing's number makes each line its own, as ERPNext asks of lines with one item.
			"description": _("{0}, {1}: {2} ({3})").format(
				unbilled[name].obligation_template, unbilled[name].period_label, unbilled[name].company, name
			),
			"qty": 1,
			"rate": unbilled[name].fee,
			"compliance_task": name,
			"sac_code": unbilled[name].sac_code or settings.default_sac,
		}
		for name in asked
	]
	start = scoped.get_value("Compliance Client", client, "billing_from")
	rates = rates_for([client])[client]
	carries_recurring = company == recurring_company_of(client, client_companies(client))
	charges = recurring_due(rates, start, month) if month and carries_recurring else []
	if charges:
		# A month's recurring charges go on one bill: the monthly draft's, or the first made by hand.
		key = key or month_key(client, company, month)
		if month_billed(key):
			frappe.throw(
				_("{0}'s recurring charges for {1} are already on a bill.").format(
					company or client_title(client), format_date(month, "MMM yyyy")
				)
			)
	for charge in charges:
		items.append(
			{
				"item_code": FEES_ITEM,
				"description": charge["description"],
				"qty": 1,
				"rate": charge["amount"],
				"sac_code": charge["sac_code"] or settings.default_sac,
			}
		)
	for done in services or []:
		items.append(service_line(rates, done, settings.default_sac))
	for line in lines or []:
		items.append(other_line(line, settings.default_sac))
	if not items:
		frappe.throw(
			_(
				"Nothing to bill {0} for: choose filings, recurring charges or services, or add a line."
			).format(client_title(client))
		)
	today = getdate(nowdate())
	# Only a firm registered for GST charges it.
	party = billing_party(client, company)
	template = tax_template_for(party.billing_state) if settings.gst_status == REGISTERED else None
	if template:
		government_fees_untaxed(items, settings.billing_company)
	bill = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": settings.billing_company,
			"customer": customer_for(client),
			"compliance_client": client,
			"billed_company": company,
			"kx_billing_key": key,
			# Kept on the bill, so a later change of GST status does not retitle bills already made.
			"bill_title": BILL_TITLES[settings.gst_status or REGISTERED],
			"posting_date": today,
			"set_posting_time": 1,
			"due_date": add_days(today, BILL_DUE_DAYS),
			"items": items,
			"taxes_and_charges": template,
			"taxes": template_taxes(template),
		}
	)
	numbering = series()
	if numbering:
		bill.naming_series = numbering
	bill.insert()
	return bill.name


# The tax lines a bill takes from its template (ERPNext's own reader also wants the person to read
# templates, which billing staff need not).
TAX_LINE_FIELDS = (
	"charge_type",
	"account_head",
	"description",
	"rate",
	"cost_center",
	"included_in_print_rate",
)


def template_taxes(template: str | None) -> list[dict]:
	if not template:
		return []
	return [
		{field: row.get(field) for field in TAX_LINE_FIELDS}
		for row in frappe.get_doc("Sales Taxes and Charges Template", template).taxes
	]


def unit_word(unit: str, qty: float) -> str:
	"""hour or hours, item or items, as the quantity reads."""
	if unit == "Per hour":
		return _("hour") if qty == 1 else _("hours")
	return _("item") if qty == 1 else _("items")


def service_line(rates: dict[tuple, dict], done: dict, default_sac: str | None) -> dict:
	"""A service done for the client, at its rate: hours or items times the rate."""
	if not isinstance(done, dict) or set(done) - {"service", "qty"}:
		frappe.throw(_("Each service done is the service and how many hours or items."))
	rate = rates.get(("Service", str(done.get("service") or "").strip()))
	if not rate or rate["unit"] not in AS_DONE:
		frappe.throw(
			_("{0} is not a service charged by the hour or item for this client.").format(done.get("service"))
		)
	qty = flt(done.get("qty"), 2)
	if qty <= 0:
		frappe.throw(_("Give how many hours or items of {0}.").format(rate["service"]))
	return {
		"item_code": HOURS_ITEM if rate["unit"] == "Per hour" else FEES_ITEM,
		"description": _("{0}, {1} {2}").format(
			rate["service"],
			frappe.format(qty, {"fieldtype": "Float"}),
			unit_word(rate["unit"], qty),
		),
		"qty": qty,
		"rate": rate["amount"],
		"sac_code": rate["sac_code"] or default_sac,
	}


def government_fees_untaxed(items: list[dict], company: str):
	"""Government fees passed on carry no GST: their lines take the company's template that taxes
	them at nothing."""
	without = scoped.get_value("Item Tax Template", {"company": company, "title": WITHOUT_GST})
	if not without:
		frappe.throw(_("Set billing up again: {0} has no {1} tax template.").format(company, WITHOUT_GST))
	for item in items:
		if item.get("item_code") == GOVERNMENT_FEES_ITEM:
			item["item_tax_template"] = without


def other_line(line: dict, default_sac: str | None = None) -> dict:
	"""A typed line: a description and amount; government fees go on the item without GST, and a
	fee carries the firm's default SAC code."""
	if not isinstance(line, dict) or set(line) - {"description", "amount", "government"}:
		frappe.throw(_("Each other line is a description, an amount and whether it is a government fee."))
	description = str(line.get("description") or "").strip()
	amount = flt(line.get("amount"))
	if not description or amount <= 0:
		frappe.throw(_("Each other line needs what it is for and an amount above zero."))
	return {
		"item_code": GOVERNMENT_FEES_ITEM if line.get("government") else FEES_ITEM,
		"description": description,
		"qty": 1,
		"rate": amount,
		"sac_code": None if line.get("government") else default_sac,
	}


def bill_of(name: str):
	"""One of the firm's bills, for those who bill; never another company's invoice."""
	check_biller()
	bill = frappe.get_doc("Sales Invoice", name)
	bill.check_permission("read")
	if bill.company != get_settings().billing_company or not bill.compliance_client:
		frappe.throw(_("{0} is not one of the firm's bills.").format(name), frappe.PermissionError)
	check_client_allowed(bill.compliance_client)
	return bill


def send_bill(name: str) -> dict:
	"""Submit a draft bill, so it is in the books, then email it to the client."""
	bill = bill_of(name)
	if bill.docstatus != 0:
		frappe.throw(_("{0} has been sent already.").format(name))
	# Money the client paid ahead goes against the bill as it is sent (ERPNext's own allocation).
	bill.allocate_advances_automatically = 1
	bill.submit()
	return {"name": bill.name, "emailed_to": email_bill(bill)}


def email_bill(bill, overdue_days: int | None = None) -> str | None:
	"""Email the bill's PDF to its company's billing email, else the client's, else the client's
	contact; the address, or None. With `overdue_days`, as a reminder that it is that many days
	late."""
	from kxcompliance.kx_compliance.reminders import sender_address

	to = billing_party(bill.compliance_client, bill.get("billed_company")).email
	sender = sender_address()
	if not to or not sender:
		return None
	frappe.sendmail(
		recipients=[to],
		sender=sender,
		subject=(
			_("Reminder: bill {0} from {1} is overdue").format(bill.name, bill.company)
			if overdue_days
			else _("Bill {0} from {1}").format(bill.name, bill.company)
		),
		message=(
			_(
				"Bill {0} was due on {1}, {2} days ago, and {3} of it is still to be paid. It is attached again."
			).format(
				bill.name,
				format_date(bill.due_date),
				overdue_days,
				frappe.format(bill.outstanding_amount, {"fieldtype": "Currency"}),
			)
			if overdue_days
			else _("Please find bill {0} for {1} attached, due on {2}.").format(
				bill.name,
				frappe.format(bill.grand_total, {"fieldtype": "Currency"}),
				format_date(bill.due_date),
			)
		),
		attachments=[
			frappe.attach_print(
				"Sales Invoice",
				bill.name,
				file_name=bill.name.replace("/", "-"),
				print_format=BILL_FORMAT,
				print_letterhead=False,  # the layout carries the firm's own heading
			)
		],
		reference_doctype="Sales Invoice",
		reference_name=bill.name,
	)
	return to


def cancel_bill(name: str):
	"""Cancel a sent bill (its filings may be billed again), or delete a draft."""
	bill = bill_of(name)
	if bill.docstatus == 0:
		frappe.delete_doc("Sales Invoice", bill.name)
	elif bill.docstatus == 1:
		bill.cancel()


def mark_filings_billed(bill, method=None):
	"""A sent bill: its filings are billed in it, each only once. A credit note for the whole of a
	filing's line lets that filing be billed again."""
	if bill.get("is_return"):
		follow_credits(bill.return_against)
		return
	filings = [row.compliance_task for row in bill.items if row.get("compliance_task")]
	if not filings:
		return
	task = frappe.qb.DocType("Compliance Task")
	elsewhere = (
		frappe.qb.from_(task)
		.select(task.name, task.billed_in)
		.where(task.name.isin(filings) & task.billed_in.isnotnull() & (task.billed_in != bill.name))
		.where(scoped.where(task))
	).run(as_dict=True)
	if elsewhere:
		frappe.throw(_("{0} is already billed in {1}.").format(elsewhere[0].name, elsewhere[0].billed_in))
	# A link kept by the bill's own submit, not a state of the filing.
	(
		frappe.qb.update(task)
		.set(task.billed_in, bill.name)
		.where(task.name.isin(filings))
		.where(scoped.where(task))
	).run()


def unmark_filings_billed(bill, method=None):
	"""A cancelled bill: its filings may be billed again. A cancelled credit note: what it credited
	is billed again."""
	if bill.get("is_return"):
		follow_credits(bill.return_against)
		return
	task = frappe.qb.DocType("Compliance Task")
	(
		frappe.qb.update(task)
		.set(task.billed_in, None)
		.where(task.billed_in == bill.name)
		.where(scoped.where(task))
	).run()


def make_monthly_drafts(today: date | None = None):
	"""On the 1st: a draft bill per client with recurring charges due or filed returns to bill, for a
	manager to check and send. Made once per client and month; one client's problem stops no other."""
	settings = get_settings()
	if settings.account_type != FIRM or not settings.billing_company:
		return
	month = get_first_day(today or nowdate())
	for client in scoped.get_all("Compliance Client", filters={"status": ("!=", "Left")}, pluck="name"):
		companies = client_companies(client)
		for company in companies or [None]:
			make_monthly_draft(client, company, companies, month)


def month_key(client: str, company: str | None, month: date) -> str:
	"""The key of a company's bill for a month: its monthly draft, or the bill its recurring
	charges went on."""
	return f"{client}|{company or ''}|{month.isoformat()[:7]}"


def month_billed(key: str) -> bool:
	return bool(scoped.exists("Sales Invoice", {"kx_billing_key": key, "docstatus": ("!=", 2)}))


def make_monthly_draft(client: str, company: str | None, companies: list[str], month: date):
	"""The month's draft for one company of a client, if it has filings to bill or carries the
	client's recurring charges and some are due. Made once per company and month."""
	key = month_key(client, company, month)
	if month_billed(key):
		return
	try:
		filings = [row.name for row in unbilled_filings(client) if company is None or row.company == company]
		recurring = company == recurring_company_of(client, companies) and recurring_due(
			rates_for([client])[client],
			scoped.get_value("Compliance Client", client, "billing_from"),
			month,
		)
		if filings or recurring:
			make_bill(client, filings=filings, month=month, key=key, company=company)
		# A job may commit as it goes, so a later company's problem loses nothing made before it.
		frappe.db.commit()
	except Exception:
		# A scheduled job: undo this company's half-made bill, keep the others, and say why.
		frappe.db.rollback()
		frappe.log_error(title=f"Monthly bill for {company or client} could not be made")


def bill_options(client: str, company: str | None = None) -> dict:
	"""What a new bill for one of a client's companies may hold: the client's companies to choose
	from, that company's unbilled filings, the recurring charges due this month if it carries them,
	and the services it may be billed for by the hour or item."""
	check_biller()
	companies = client_companies(client)
	company = company or (companies[0] if companies else None)
	if company and company not in companies:
		frappe.throw(_("{0} is not one of {1}'s companies.").format(company, client_title(client)))
	month = get_first_day(nowdate())
	rates = rates_for([client])[client]
	start = scoped.get_value("Compliance Client", client, "billing_from")
	recurring_to = recurring_company_of(client, companies)
	return {
		"companies": companies,
		"company": company,
		"recurring_company": recurring_to,
		"filings": [row for row in unbilled_filings(client) if company is None or row.company == company],
		# Due and not yet on a bill this month.
		"recurring": recurring_due(rates, start, month)
		if company == recurring_to and not month_billed(month_key(client, company, month))
		else [],
		"recurring_without_start": recurring_without_start(rates, start) if company == recurring_to else [],
		"services": [line for line in rates.values() if line["unit"] in AS_DONE],
	}


BILL_FIELDS = (
	"name",
	"compliance_client",
	"billed_company",
	"customer_name",
	"status",
	"docstatus",
	"posting_date",
	"due_date",
	"net_total",
	"total_taxes_and_charges",
	"grand_total",
	"rounded_total",
	"outstanding_amount",
	"currency",
	"is_return",
	"return_against",
	"remarks",
)


def line_text(description: str | None, filing: str | None) -> str:
	"""A bill line's text without the filing number it ends with."""
	text = description or ""
	return text.removesuffix(f" ({filing})") if filing else text


def bill_detail(name: str) -> dict:
	"""A bill as its page shows it: lines, tax, totals, what is due."""
	bill = bill_of(name)
	credited = credited_lines(bill.name) if bill.docstatus == 1 and not bill.is_return else None
	return {
		**{field: bill.get(field) for field in BILL_FIELDS},
		"client_name": client_title(bill.compliance_client),
		"items": [
			{
				"name": row.name,
				# The page links the filing by its number, so the number is not repeated in the text.
				"description": line_text(row.description, row.get("compliance_task")),
				"amount": row.amount,
				"filing": row.get("compliance_task"),
				"creditable": creditable(row, credited)[1] if credited is not None else 0,
			}
			for row in bill.items
		],
		"taxes": [{"description": row.description, "amount": row.tax_amount} for row in bill.taxes],
		"payments": payments_of(bill.name) if bill.docstatus == 1 else [],
		"credit_notes": credit_notes_of(bill.name) if bill.docstatus == 1 else [],
		"written_off": written_off(bill.name) if bill.docstatus == 1 else [],
		"advance_held": advance_held(bill.customer) if bill.docstatus == 0 else 0,
		"modes": list(PAYMENT_MODES),
		# Any of the client's companies may pay this bill.
		"companies": client_companies(bill.compliance_client) if bill.compliance_client else [],
	}


def payer(client: str, paid_by: str | None) -> str | None:
	"""Which of the client's companies the money came from, when the firm notes it."""
	if paid_by and paid_by not in client_companies(client):
		frappe.throw(_("Paid by: {0} is not one of {1}'s companies.").format(paid_by, client_title(client)))
	return paid_by or None


def record_payment(
	name: str,
	amount: float,
	paid_on: str,
	mode: str,
	reference: str | None = None,
	tds: float = 0,
	paid_by: str | None = None,
) -> str:
	"""A payment against a sent bill, in full or in part, as ERPNext's own Payment Entry from the
	bill. TDS the client deducted is recorded beside it, so the bill is settled by both. Any of the
	client's companies may pay the bill of another; `paid_by` notes which did."""
	bill = bill_of(name)
	paid_by = payer(bill.compliance_client, paid_by)
	if bill.docstatus != 1:
		frappe.throw(_("Send {0} before recording a payment against it.").format(name))
	amount, tds = flt(amount, 2), flt(tds, 2)
	if amount <= 0 or tds < 0:
		frappe.throw(_("A payment is an amount above zero, and TDS zero or more."))
	due = flt(bill.outstanding_amount, 2)
	if amount + tds > due:
		frappe.throw(
			_("{0} and TDS {1} come to more than the {2} still due on {3}.").format(amount, tds, due, name)
		)
	if getdate(paid_on) > getdate(nowdate()):
		frappe.throw(_("A payment cannot be dated {0}, after today.").format(format_date(paid_on)))
	if mode not in PAYMENT_MODES:
		frappe.throw(_("Pay by one of {0}, not {1}.").format(", ".join(PAYMENT_MODES), mode))
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	account = payment_account(bill.company, mode)
	entry = get_payment_entry("Sales Invoice", bill.name, party_amount=amount)
	entry.posting_date = getdate(paid_on)
	entry.mode_of_payment = mode
	if account:
		entry.paid_to = account
	entry.paid_amount = entry.received_amount = amount
	entry.reference_no = (reference or "").strip() or mode
	entry.reference_date = getdate(paid_on)
	entry.paid_by_company = paid_by
	for row in entry.references:
		row.allocated_amount = amount + tds
	if tds:
		entry.append(
			"deductions",
			{
				"account": scoped.get_value(
					"Account", {"company": bill.company, "account_name": TDS_ACCOUNT, "is_group": 0}
				),
				"cost_center": scoped.get_value("Company", bill.company, "cost_center"),
				"amount": tds,
				"description": _("TDS deducted by the client"),
			},
		)
	entry.insert()
	entry.submit()
	return entry.name


def payments_of(bill: str) -> list[dict]:
	"""The payments received against a bill, oldest first, each with any TDS deducted."""
	reference = frappe.qb.DocType("Payment Entry Reference")
	entry = frappe.qb.DocType("Payment Entry")
	rows = (
		frappe.qb.from_(reference)
		.join(entry)
		.on(entry.name == reference.parent)
		.select(
			entry.name,
			entry.posting_date,
			entry.mode_of_payment,
			entry.reference_no,
			entry.paid_amount,
			reference.allocated_amount,
		)
		.where(
			(reference.reference_doctype == "Sales Invoice")
			& (reference.reference_name == bill)
			& (entry.docstatus == 1)
		)
		.where(scoped.where(reference))
		.where(scoped.where(entry))
		.orderby(entry.posting_date)
		.orderby(entry.name)
	).run(as_dict=True)
	# A payment may settle several bills (an advance used against each as they are sent), so its
	# TDS is shared by what it settled of each, and what it paid on this bill is the rest.
	names = [row.name for row in rows] or [""]
	deducted: dict[str, float] = {}
	for line in scoped.get_all(
		"Payment Entry Deduction",
		filters={"parenttype": "Payment Entry", "parent": ("in", names)},
		fields=["parent", "amount"],
	):
		deducted[line.parent] = deducted.get(line.parent, 0) + flt(line.amount)
	settled = dict(
		(
			frappe.qb.from_(reference)
			.select(reference.parent, Sum(reference.allocated_amount))
			.where((reference.parent.isin(names)) & (reference.reference_doctype == "Sales Invoice"))
			.where(scoped.where(reference))
			.groupby(reference.parent)
		).run()
	)
	for row in rows:
		total = flt(settled.get(row.name))
		row.tds = flt(deducted.get(row.name, 0) * flt(row.allocated_amount) / total, 2) if total else 0
		row.paid_amount = flt(row.allocated_amount - row.tds, 2)
	return rows


def payment_of(name: str):
	"""A payment to the firm, for those who bill: one against its bills, or an advance."""
	if not isinstance(name, str) or not scoped.exists("Payment Entry", name):
		frappe.throw(_("Payment {0} does not exist.").format(name), frappe.DoesNotExistError)
	entry = frappe.get_doc("Payment Entry", name)
	bills = [row.reference_name for row in entry.references if row.reference_doctype == "Sales Invoice"]
	if bills:
		bill_of(bills[0])  # who may bill, and a bill of the firm's
	else:
		check_biller()
		if entry.company != get_settings().billing_company or entry.party_type != "Customer":
			frappe.throw(_("{0} is not a payment to the firm.").format(name), frappe.PermissionError)
		check_client_allowed(client_of_payment(entry))
	return entry


def client_of_payment(entry) -> str | None:
	"""The client who paid: the customer the payment is from is that client's."""
	return scoped.get_value("Compliance Client", {"customer": entry.party}, "name") if entry.party else None


def payment_detail(name: str) -> dict:
	"""A payment as its page shows it: who paid, when and how, TDS, the bills it settled and what
	is still held as an advance."""
	entry = payment_of(name)
	client = client_of_payment(entry)
	settled = [row for row in entry.references if row.reference_doctype == "Sales Invoice"]
	bills = {
		row.name: row
		for row in scoped.get_all(
			"Sales Invoice",
			filters={"name": ("in", [row.reference_name for row in settled] or [""])},
			fields=["name", "posting_date", "grand_total", "rounded_total", "outstanding_amount"],
		)
	}
	emails = (
		scoped.get_value("Compliance Client", client, ["billing_email", "contact_email"], as_dict=True)
		if client
		else None
	)
	return {
		"name": entry.name,
		"docstatus": entry.docstatus,
		"client": client,
		"client_name": client_title(client),
		"party_name": entry.party_name,
		"paid_by_company": entry.paid_by_company,
		"posting_date": entry.posting_date,
		"mode_of_payment": entry.mode_of_payment,
		"reference_no": entry.reference_no if entry.reference_no != entry.mode_of_payment else None,
		"paid_amount": flt(entry.paid_amount),
		"tds": flt(sum(flt(row.amount) for row in entry.deductions)),
		"unallocated_amount": flt(entry.unallocated_amount),
		"currency": entry.paid_to_account_currency or "INR",
		"bills": [
			{
				"name": row.reference_name,
				"allocated": flt(row.allocated_amount),
				"posting_date": bills.get(row.reference_name, {}).get("posting_date"),
				"total": flt(
					bills.get(row.reference_name, {}).get("rounded_total")
					or bills.get(row.reference_name, {}).get("grand_total")
				),
				"still_due": flt(bills.get(row.reference_name, {}).get("outstanding_amount")),
			}
			for row in settled
		],
		"email_to": emails and (emails.billing_email or emails.contact_email),
		"emailed": scoped.count(
			"Communication",
			{"reference_doctype": "Payment Entry", "reference_name": entry.name, "sent_or_received": "Sent"},
		),
	}


def email_receipt(name: str) -> str:
	"""Email a payment's receipt to the client's billing email, else its contact; the address."""
	from kxcompliance.kx_compliance.reminders import sender_address

	entry = payment_of(name)
	if entry.docstatus != 1:
		frappe.throw(_("{0} is cancelled; it has no receipt to send.").format(name))
	client = client_of_payment(entry)
	address = (
		scoped.get_value("Compliance Client", client, ["billing_email", "contact_email"], as_dict=True)
		if client
		else None
	)
	to = address and (address.billing_email or address.contact_email)
	if not to:
		frappe.throw(
			_("{0} has no billing or contact email; give it one on the client's form.").format(
				client_title(client)
			)
		)
	sender = sender_address()
	if not sender:
		frappe.throw(
			_("The app has no email account to send from; set one in Settings, Reminders and email.")
		)
	frappe.sendmail(
		recipients=[to],
		sender=sender,
		subject=_("Receipt {0} from {1}").format(entry.name, entry.company),
		message=_("Thank you for your payment of {0} on {1}. The receipt is attached.").format(
			frappe.format(entry.paid_amount, {"fieldtype": "Currency"}), format_date(entry.posting_date)
		),
		attachments=[
			frappe.attach_print(
				"Payment Entry",
				entry.name,
				file_name=entry.name,
				print_format=RECEIPT_FORMAT,
				print_letterhead=False,  # the layout carries the firm's own heading
			)
		],
		reference_doctype="Payment Entry",
		reference_name=entry.name,
	)
	return to


def cancel_payment(name: str):
	"""Cancel a payment recorded against one of the firm's bills (the bill is due again), or an
	advance a client paid."""
	entry = payment_of(name)
	if entry.docstatus != 1:
		frappe.throw(_("{0} is not a recorded payment.").format(name))
	entry.cancel()


# The Billing list's tabs, and what each holds.
BILL_VIEWS = {
	"drafts": [["docstatus", "=", 0]],
	"unpaid": [["docstatus", "=", 1], ["outstanding_amount", ">", 0]],
	"paid": [["docstatus", "=", 1], ["outstanding_amount", "<=", 0]],
	"all": [],
}
LIST_FIELDS = [
	"name",
	"compliance_client",
	"billed_company",
	"customer_name",
	"posting_date",
	"due_date",
	"grand_total",
	"rounded_total",
	"outstanding_amount",
	"docstatus",
	"status",
	"is_return",
	"currency",
]
TOTALS = [{"COUNT": "*", "as": "count"}, {"SUM": "outstanding_amount", "as": "due"}]


def bill_filters(view: str, client: str | None, text: str | None) -> tuple[list, list | None]:
	"""The firm's bills in a tab, of one client if chosen, matching the words typed."""
	if view not in BILL_VIEWS:
		frappe.throw(_("{0} is not a list of bills.").format(view))
	filters = [
		["company", "=", get_settings().billing_company],
		["compliance_client", "is", "set"],
		*BILL_VIEWS[view],
	]
	if client:
		check_client_allowed(client)
		filters.append(["compliance_client", "=", client])
	elif billable_clients() is not None:
		filters.append(["compliance_client", "in", list(billable_clients()) or [""]])
	text = (text or "").strip()
	matching = [["name", "like", f"%{text}%"], ["customer_name", "like", f"%{text}%"]] if text else None
	return filters, matching


def bills(view: str, client: str | None, text: str | None, start: int, limit: int) -> dict:
	"""One page of the firm's bills in a tab, newest first, with how many there are in all."""
	check_biller()
	filters, matching = bill_filters(view, client, text)
	rows = frappe.get_list(
		"Sales Invoice",
		filters=filters,
		or_filters=matching,
		fields=LIST_FIELDS,
		order_by="posting_date desc, name desc",
		start=start,
		page_length=limit,
	)
	total = frappe.get_list("Sales Invoice", filters=filters, or_filters=matching, fields=TOTALS)
	titles = client_titles(row.compliance_client for row in rows)
	for row in rows:
		row.client_name = titles.get(row.compliance_client, row.compliance_client)
	return {"rows": rows, "total": total[0]["count"] if total else 0}


def bill_counts(client: str | None, text: str | None) -> dict:
	"""Each tab's count and what is still due in it."""
	check_biller()
	counts = {}
	for view in BILL_VIEWS:
		filters, matching = bill_filters(view, client, text)
		row = frappe.get_list("Sales Invoice", filters=filters, or_filters=matching, fields=TOTALS)
		counts[view] = {"count": row[0]["count"] if row else 0, "due": flt(row[0]["due"]) if row else 0}
	return counts


def client_billing(client: str, own: bool) -> dict:
	"""A client's bills and balance. `own` is the client's own login, which sees only bills sent
	to it; the firm also sees drafts and what it has yet to bill. The caller has checked who may
	see this; a client's login reads its bills here, as it may not read ERPNext's invoices."""
	from kxcompliance.kx_compliance.client_reports import financial_year

	company = get_settings().billing_company
	if not company:
		return {"bills": [], "outstanding": 0, "overdue": 0}
	from_date, to_date = financial_year()
	sent = {"company": company, "compliance_client": client, "docstatus": 1}
	shown = sent if own else {**sent, "docstatus": ("in", (0, 1))}
	bills_shown = scoped.get_all(
		"Sales Invoice", filters=shown, fields=LIST_FIELDS, order_by="posting_date desc, name desc", limit=10
	)
	due = scoped.get_all(
		"Sales Invoice",
		filters={**sent, "outstanding_amount": (">", 0)},
		fields=["outstanding_amount", "due_date"],
	)
	today = getdate(nowdate())
	result = {
		"bills": bills_shown,
		"outstanding": sum(flt(row.outstanding_amount) for row in due),
		"overdue": sum(flt(row.outstanding_amount) for row in due if getdate(row.due_date) < today),
		# The dates a statement of account starts as.
		"year": {"from_date": from_date, "to_date": to_date},
	}
	if not own:
		unbilled = unbilled_filings(client)
		result["unbilled_count"] = len(unbilled)
		result["unbilled_total"] = sum(row.fee for row in unbilled)
	return result


# Filings that will not be done, so are not expected to be billed.
NOT_EXPECTED = ("Not Applicable", "Cancelled")


def client_summary(client: str) -> dict:
	"""Where a client stands with the firm in this financial year: what it is expected to pay, what
	has been billed, received, credited and written off, what is due and how late, and its rates."""
	from kxcompliance.kx_compliance.client_reports import financial_year

	from_date, to_date = financial_year()
	values = scoped.get_value(
		"Compliance Client", client, ["customer", "rate_card", "billing_from"], as_dict=True
	)
	rates = rates_for([client])[client]
	ageing = outstanding_by_client(client, getdate(nowdate()))
	unbilled = unbilled_filings(client)
	return {
		"year": {"from_date": from_date, "to_date": to_date},
		"commitment": commitment(client, rates, values.billing_from, from_date, to_date),
		"recurring_without_start": recurring_without_start(rates, values.billing_from),
		"activity": year_activity(client, values.customer, from_date, to_date),
		"outstanding": ageing[0] if ageing else {"outstanding": 0} | {key: 0 for key, _low, _high in AGEING},
		"advance": advance_held(values.customer),
		"unbilled_count": len(unbilled),
		"unbilled_total": sum(row.fee for row in unbilled),
		"rate_card": values.rate_card or default_card(),
		"rate_card_title": rate_card_title(values.rate_card or default_card()),
		"rates": list(rates.values()),
		"payments": payments(client, None, 0, 5)["rows"],
		"by_company": [
			{
				"key": section["key"],
				"title": section["title"],
				"billed": section["billed"],
				"received": flt(section["received"] + section["tds"], 2),
				"credited": flt(section["credited"] + section["written_off"], 2),
				"balance": section["closing"],
			}
			for section in statement(client, from_date, to_date)["sections"]
		],
	}


def commitment(client: str, rates: dict[tuple, dict], start, from_date, to_date) -> dict:
	"""What a client is expected to pay in the year: each recurring charge for every period that
	starts in it (from the client's `start`), and the rate of each filing due in it."""
	recurring = []
	for line in rates.values():
		months = RECURRING_MONTHS.get(line["unit"])
		if not (months and start and line["amount"]):
			continue
		periods = 0
		month = get_first_day(from_date)
		while month <= getdate(to_date):
			periods += starts_period(start, months, month)
			month = add_months(month, 1)
		if periods:
			recurring.append(
				{
					"service": line["service"],
					"unit": line["unit"],
					"periods": periods,
					"rate": flt(line["amount"]),
					"amount": flt(line["amount"]) * periods,
				}
			)
	filings = []
	unpriced = 0
	for row in filings_due(client, from_date, to_date):
		rate = rates.get(("Return", row.obligation_template))
		if not (rate and rate["amount"]):
			unpriced += row.count
			continue
		filings.append(
			{
				"return": row.obligation_template,
				"count": row.count,
				"rate": flt(rate["amount"]),
				"amount": flt(rate["amount"]) * row.count,
			}
		)
	return {
		"recurring": recurring,
		"filings": filings,
		"unpriced": unpriced,
		"total": sum(row["amount"] for row in recurring) + sum(row["amount"] for row in filings),
	}


def filings_due(client: str, from_date, to_date) -> list[dict]:
	"""How many of each return the client's companies have due in these dates, not counting those
	that will not be done."""
	from frappe.query_builder.functions import Count

	task = frappe.qb.DocType("Compliance Task")
	profile = frappe.qb.DocType("Company Compliance Profile")
	return (
		frappe.qb.from_(task)
		.join(profile)
		.on(profile.company == task.company)
		.select(task.obligation_template, Count(task.name).as_("count"))
		.where(
			(profile.client == client)
			& task.effective_due_date.between(from_date, to_date)
			& task.status.notin(NOT_EXPECTED)
		)
		.where(scoped.where(task))
		.where(scoped.where(profile))
		.groupby(task.obligation_template)
		.orderby(task.obligation_template)
	).run(as_dict=True)


def year_activity(client: str | None, customer: str | None, from_date, to_date) -> dict:
	"""What was billed, credited, received, deducted as TDS and written off in these dates: for one
	client (and its customer), or with no client, for every client the firm bills."""
	from frappe.query_builder import Case

	company = get_settings().billing_company
	invoice = frappe.qb.DocType("Sales Invoice")
	total = Case().when(invoice.rounded_total != 0, invoice.rounded_total).else_(invoice.grand_total)
	billed, credited = (
		frappe.qb.from_(invoice)
		.select(
			Sum(Case().when(invoice.is_return == 0, total).else_(0)),
			Sum(Case().when(invoice.is_return == 1, -total).else_(0)),
		)
		.where(
			(invoice.company == company)
			& (invoice.compliance_client == client if client else invoice.compliance_client.isnotnull())
			& (invoice.docstatus == 1)
			& invoice.posting_date.between(from_date, to_date)
		)
		.where(scoped.where(invoice))
	).run()[0]
	activity = {"billed": flt(billed), "credited": flt(credited), "received": 0, "tds": 0, "written_off": 0}
	if client and not customer:
		return activity  # never billed, so nothing paid either
	entry = frappe.qb.DocType("Payment Entry")
	paid_in = (
		(entry.company == company)
		& (entry.party_type == "Customer")
		& ((entry.party == customer) if customer else entry.party.isnotnull())
		& (entry.payment_type == "Receive")
		& (entry.docstatus == 1)
		& entry.posting_date.between(from_date, to_date)
		& scoped.where(entry)
	)
	activity["received"] = flt(
		frappe.qb.from_(entry).select(Sum(entry.paid_amount)).where(paid_in).run()[0][0]
	)
	deduction = frappe.qb.DocType("Payment Entry Deduction")
	activity["tds"] = flt(
		frappe.qb.from_(deduction)
		.join(entry)
		.on(entry.name == deduction.parent)
		.select(Sum(deduction.amount))
		.where(paid_in & (deduction.parenttype == "Payment Entry"))
		.where(scoped.where(deduction))
		.run()[0][0]
	)
	journal = frappe.qb.DocType("Journal Entry")
	line = frappe.qb.DocType("Journal Entry Account")
	activity["written_off"] = flt(
		frappe.qb.from_(line)
		.join(journal)
		.on(journal.name == line.parent)
		.select(Sum(line.credit_in_account_currency - line.debit_in_account_currency))
		.where(
			(journal.company == company)
			& (journal.voucher_type == "Write Off Entry")
			& (journal.docstatus == 1)
			& journal.posting_date.between(from_date, to_date)
			& (line.party_type == "Customer")
			& ((line.party == customer) if customer else line.party.isnotnull())
		)
		.where(scoped.where(line))
		.where(scoped.where(journal))
		.run()[0][0]
	)
	return activity


def billing_summary(client: str | None = None) -> dict:
	"""The firm's billing this financial year, for one client or all: billed, received, TDS,
	credited and written off; what is still due by how late; month by month; the clients owing
	most; and what is filed but not billed."""
	from kxcompliance.kx_compliance.client_reports import financial_year

	check_biller()
	if client:
		check_client_allowed(client)
	elif billable_clients() is not None:
		# The firm's totals are for those who bill every client; the rest choose one of theirs.
		frappe.throw(_("Choose one of your clients to see its billing."), frappe.PermissionError)
	from_date, to_date = financial_year()
	customer = scoped.get_value("Compliance Client", client, "customer") if client else None
	owing = outstanding_by_client(client, getdate(nowdate()))
	unbilled = unbilled_for_clients(client)
	unbilled_by_client: dict[str, dict] = {}
	for row in unbilled:
		line = unbilled_by_client.setdefault(
			row.client, {"client": row.client, "client_name": row.client_name, "count": 0, "total": 0}
		)
		line["count"] += 1
		line["total"] = flt(line["total"] + flt(row.fee), 2)
	return {
		"year": {"from_date": from_date, "to_date": to_date},
		"activity": year_activity(client, customer, from_date, to_date),
		"ageing": {
			key: flt(sum(line[key] for line in owing), 2)
			for key in ["outstanding", *(k for k, _l, _h in AGEING)]
		},
		"by_month": billing_by_month(from_date, to_date, client),
		"owing_most": sorted(owing, key=lambda line: -line["outstanding"])[:5],
		"unbilled": {
			"count": len(unbilled),
			"total": flt(sum(flt(row.fee) for row in unbilled), 2),
			"clients": sorted(unbilled_by_client.values(), key=lambda line: -line["total"])[:5],
		},
	}


# Where an entry on a client's account sits on its statement: under the company its bill was for,
# under the client as a whole for bills made before bills named a company, or as money held ahead.
AHEAD = "ahead"
# Within one entry (a payment), what it paid comes before the TDS deducted with it.
ENTRY_ORDER = {"bill": 0, "credit": 0, "payment": 0, "tds": 1, "write_off": 0}


def account_entries(customer: str, to_date, own: bool = False) -> list[dict]:
	"""Every entry on a client's account up to `to_date`, in date order: each bill, credit note,
	payment (split by the bills it settled, with its TDS), write-off, and money held ahead. Each
	says the company it belongs to and the bill it is against. `own` is the client's copy, which
	does not give the firm's reasons for writing off."""
	company = get_settings().billing_company
	to_date = getdate(to_date)
	bills = {
		row.name: row
		for row in scoped.get_all(
			"Sales Invoice",
			filters={"company": company, "customer": customer, "docstatus": 1},
			fields=[
				"name",
				"posting_date",
				"due_date",
				"is_return",
				"return_against",
				"remarks",
				"billed_company",
				"grand_total",
				"rounded_total",
				"creation",
			],
		)
	}
	entries = []
	for bill in bills.values():
		if getdate(bill.posting_date) > to_date:
			continue
		total = flt(bill.rounded_total or bill.grand_total)
		if bill.is_return:
			original = bills.get(bill.return_against) or frappe._dict()
			entries.append(
				entry(
					bill.posting_date,
					"credit",
					bill.name,
					_("Credit note against {0}").format(bill.return_against),
					bill.billed_company or original.billed_company,
					bill.return_against,
					credit=-total,
					made=bill.creation,
				)
			)
		else:
			entries.append(
				entry(
					bill.posting_date,
					"bill",
					bill.name,
					_("Bill, due {0}").format(format_date(bill.due_date)),
					bill.billed_company,
					bill.name,
					debit=total,
					made=bill.creation,
				)
			)
	entries += payment_entries(customer, company, to_date, bills)
	entries += write_off_entries(customer, company, to_date, bills, own)
	# By date, then in the order they were made.
	return sorted(entries, key=lambda row: (row["date"], row.pop("made"), ENTRY_ORDER[row["kind"]]))


def entry(
	date, kind: str, name: str, detail: str, company, bill, debit: float = 0, credit: float = 0, made=None
) -> dict:
	return {
		"made": str(made or ""),
		"date": getdate(date),
		"kind": kind,
		"name": name,
		"detail": detail,
		"company": company,
		"bill": bill,
		"debit": flt(debit, 2),
		"credit": flt(credit, 2),
	}


def payment_entries(customer: str, company: str, to_date, bills: dict) -> list[dict]:
	"""Each payment as the statement shows it: what it paid on each bill, under that bill's
	company, its TDS shared across those bills as they were settled, and what is still held ahead."""
	payment = frappe.qb.DocType("Payment Entry")
	reference = frappe.qb.DocType("Payment Entry Reference")
	rows = (
		frappe.qb.from_(payment)
		.left_join(reference)
		.on(
			(reference.parent == payment.name)
			& (reference.reference_doctype == "Sales Invoice")
			& scoped.where(reference)
		)
		.select(
			payment.name,
			payment.posting_date,
			payment.creation,
			payment.mode_of_payment,
			payment.reference_no,
			payment.unallocated_amount,
			reference.reference_name,
			reference.allocated_amount,
		)
		.where(
			(payment.company == company)
			& (payment.party_type == "Customer")
			& (payment.party == customer)
			& (payment.payment_type == "Receive")
			& (payment.docstatus == 1)
			& (payment.posting_date <= to_date)
		)
		.where(scoped.where(payment))
		.orderby(payment.posting_date)
		.orderby(payment.name)
	).run(as_dict=True)
	payments: dict[str, list] = {}
	for row in rows:
		payments.setdefault(row.name, []).append(row)
	deducted: dict[str, float] = {}
	for row in scoped.get_all(
		"Payment Entry Deduction",
		filters={"parenttype": "Payment Entry", "parent": ("in", list(payments) or [""])},
		fields=["parent", "amount"],
	):
		deducted[row.parent] = deducted.get(row.parent, 0) + flt(row.amount)
	entries = []
	for name, refs in payments.items():
		first = refs[0]
		reference = first.reference_no if first.reference_no != first.mode_of_payment else None
		how = ", ".join(part for part in (first.mode_of_payment, reference) if part)
		settled = [row for row in refs if row.reference_name]
		allocated = sum(flt(row.allocated_amount) for row in settled)
		tds_left = flt(deducted.get(name), 2)
		for index, row in enumerate(settled):
			# TDS goes with each bill by its share of the payment; the last takes what is left.
			share = (
				tds_left
				if index == len(settled) - 1
				else flt(deducted.get(name, 0) * flt(row.allocated_amount) / allocated, 2)
			)
			tds_left = flt(tds_left - share, 2)
			bill = bills.get(row.reference_name) or frappe._dict()
			entries.append(
				entry(
					first.posting_date,
					"payment",
					name,
					_("Received for {0}: {1}").format(row.reference_name, how)
					if how
					else _("Received for {0}").format(row.reference_name),
					bill.billed_company,
					row.reference_name,
					credit=flt(row.allocated_amount) - share,
					made=first.creation,
				)
			)
			if share:
				entries.append(
					entry(
						first.posting_date,
						"tds",
						name,
						_("TDS deducted on {0}").format(row.reference_name),
						bill.billed_company,
						row.reference_name,
						credit=share,
						made=first.creation,
					)
				)
		if flt(first.unallocated_amount) > 0:
			entries.append(
				entry(
					first.posting_date,
					"payment",
					name,
					_("Received ahead: {0}").format(how) if how else _("Received ahead"),
					AHEAD,
					None,
					credit=first.unallocated_amount,
					made=first.creation,
				)
			)
	return entries


def write_off_entries(customer: str, company: str, to_date, bills: dict, own: bool) -> list[dict]:
	journal = frappe.qb.DocType("Journal Entry")
	line = frappe.qb.DocType("Journal Entry Account")
	rows = (
		frappe.qb.from_(line)
		.join(journal)
		.on(journal.name == line.parent)
		.select(
			journal.name,
			journal.posting_date,
			journal.creation,
			journal.user_remark,
			line.reference_name,
			(line.credit_in_account_currency - line.debit_in_account_currency).as_("amount"),
		)
		.where(
			(journal.company == company)
			& (journal.voucher_type == "Write Off Entry")
			& (journal.docstatus == 1)
			& (journal.posting_date <= to_date)
			& (line.party_type == "Customer")
			& (line.party == customer)
			& (line.reference_type == "Sales Invoice")
		)
		.where(scoped.where(line))
		.where(scoped.where(journal))
	).run(as_dict=True)
	return [
		entry(
			row.posting_date,
			"write_off",
			row.name,
			# A write-off is the firm's own decision; the client is not told why (WriteOffDialog).
			_("Balance adjusted") if own or not row.user_remark else row.user_remark,
			(bills.get(row.reference_name) or frappe._dict()).billed_company,
			row.reference_name,
			credit=row.amount,
			made=row.creation,
		)
		for row in rows
	]


SUMMED = {
	"bill": "billed",
	"credit": "credited",
	"payment": "received",
	"tds": "tds",
	"write_off": "written_off",
}


def statement(client: str, from_date, to_date, own: bool = False) -> dict:
	"""A client's statement of account for these dates: a summary, then a section per company
	(its balance before the dates, each entry with the balance after it, and its balance at the
	end), money held ahead, and the bills still open at the end with how late they are. A balance
	above zero is owed to the firm; below zero, the client has paid ahead."""
	from_date, to_date = getdate(from_date), getdate(to_date)
	if from_date > to_date:
		frappe.throw(
			_("The statement's start, {0}, is after its end, {1}.").format(
				format_date(from_date), format_date(to_date)
			)
		)
	customer = scoped.get_value("Compliance Client", client, "customer")
	entries = account_entries(customer, to_date, own) if customer else []
	sections: dict = {}
	for row in entries:
		section = sections.setdefault(
			row["company"],
			{"opening": 0, "rows": []} | dict.fromkeys(SUMMED.values(), 0),
		)
		if row["date"] < from_date:
			section["opening"] = flt(section["opening"] + row["debit"] - row["credit"], 2)
			continue
		section["rows"].append(row)
		section[SUMMED[row["kind"]]] = flt(section[SUMMED[row["kind"]]] + row["debit"] + row["credit"], 2)
	shown = []
	for key in sorted(sections, key=lambda key: (key is None, key == AHEAD, key or "")):
		section = sections[key]
		if not section["rows"] and not section["opening"]:
			continue
		balance = section["opening"]
		for row in section["rows"]:
			balance = flt(balance + row["debit"] - row["credit"], 2)
			row["balance"] = balance
		section.update(key=key, closing=balance, **section_heading(client, key))
		shown.append(section)
	today = min(to_date, getdate(nowdate()))
	open_bills = still_open(entries, today)
	return {
		"from_date": from_date,
		"to_date": to_date,
		"summary": {
			"opening": flt(sum(section["opening"] for section in shown), 2),
			**{field: flt(sum(section[field] for section in shown), 2) for field in SUMMED.values()},
			"closing": flt(sum(section["closing"] for section in shown), 2),
		},
		"sections": shown,
		"open_bills": open_bills,
		"ageing": {
			key: flt(sum(bill["due"] for bill in open_bills if bill["bucket"] == key), 2)
			for key, _low, _high in AGEING
		},
	}


def section_heading(client: str, key) -> dict:
	if key == AHEAD:
		return {"title": _("Paid ahead, not yet used"), "gstin": None}
	if key is None:
		return {"title": _("Billed to the client as a whole"), "gstin": None}
	return {"title": key, "gstin": billing_party(client, key).gstin}


def still_open(entries: list[dict], today) -> list[dict]:
	"""The bills with something still due after these entries, with how late each is on `today`."""
	bills: dict[str, dict] = {}
	for row in entries:
		if row["kind"] == "bill":
			bills[row["name"]] = {
				"name": row["name"],
				"company": row["company"],
				"date": row["date"],
				"total": row["debit"],
				"due": row["debit"],
			}
	for row in entries:
		if row["kind"] != "bill" and row["bill"] in bills:
			bills[row["bill"]]["due"] = flt(bills[row["bill"]]["due"] - row["credit"] + row["debit"], 2)
	due_dates = dict(
		scoped.get_all(
			"Sales Invoice",
			filters={"name": ("in", list(bills) or [""])},
			fields=["name", "due_date"],
			as_list=True,
		)
	)
	found = []
	for bill in bills.values():
		if bill["due"] <= 0.005:
			continue
		due_date = getdate(due_dates.get(bill["name"]) or bill["date"])
		found.append(
			{
				**bill,
				"due_date": due_date,
				"days_late": max((getdate(today) - due_date).days, 0),
				"bucket": ageing_bucket(due_date, today),
			}
		)
	return sorted(found, key=lambda bill: (bill["due_date"], bill["name"]))


def statement_html(client: str, from_date, to_date, own: bool = False) -> str:
	"""The statement of account as printed, with the firm's and the client's logos."""
	# The app's own template file, never one a user wrote.
	return frappe.render_template(  # nosemgrep
		"templates/statement_of_account.html",
		{
			"statement": statement(client, from_date, to_date, own),
			"firm": firm_details(),
			"client": billing_party(client),
			"ageing_labels": AGEING_LABELS,
			"own": own,
			"currency": scoped.get_value("Company", get_settings().billing_company, "default_currency")
			or "INR",
		},
	)


# How late a bill is, by days past its due date: the columns of Billing Outstanding.
AGEING = (
	("not_due", None, 0),
	("late_30", 1, 30),
	("late_60", 31, 60),
	("late_90", 61, 90),
	("late_more", 91, None),
)


# What each column is called; translated where it is shown.
AGEING_LABELS = {
	"not_due": "Not due yet",
	"late_30": "1 to 30 days late",
	"late_60": "31 to 60 days late",
	"late_90": "61 to 90 days late",
	"late_more": "Over 90 days late",
}


def ageing_bucket(due_date, today) -> str:
	"""Which ageing column a bill falls in on `today`."""
	late = (getdate(today) - getdate(due_date)).days
	for key, low, high in AGEING:
		if (low is None or late >= low) and (high is None or late <= high):
			return key
	return AGEING[-1][0]


def outstanding_by_client(client: str | None, today) -> list[dict]:
	"""Each client's sent bills still due, split by how late they are."""
	invoice = frappe.qb.DocType("Sales Invoice")
	query = (
		frappe.qb.from_(invoice)
		.select(invoice.compliance_client, invoice.due_date, invoice.outstanding_amount)
		.where(
			(invoice.company == get_settings().billing_company)
			& invoice.compliance_client.isnotnull()
			& (invoice.docstatus == 1)
			& (invoice.outstanding_amount > 0)
		)
		.where(scoped.where(invoice))
	)
	if client:
		query = query.where(invoice.compliance_client == client)
	clients: dict[str, dict] = {}
	for row in query.run(as_dict=True):
		line = clients.setdefault(
			row.compliance_client,
			{"client": row.compliance_client, "bills": 0, "outstanding": 0, "oldest_due": row.due_date}
			| {key: 0 for key, _low, _high in AGEING},
		)
		line["bills"] += 1
		line["outstanding"] += flt(row.outstanding_amount)
		line[ageing_bucket(row.due_date, today)] += flt(row.outstanding_amount)
		line["oldest_due"] = min(getdate(line["oldest_due"]), getdate(row.due_date))
	titles = client_titles(clients)
	for line in clients.values():
		line["client_name"] = titles.get(line["client"], line["client"])
	return sorted(clients.values(), key=lambda line: (-line["late_more"], -line["outstanding"]))


def billing_by_month(from_date, to_date, client: str | None) -> list[dict]:
	"""The firm's sent bills month by month: how many, before GST, GST, the total (as rounded on
	the bill), how much of that is settled (paid, credited or written off) and still due; and the
	credit notes made in the month, apart, so a credit is not counted as a bill."""
	from frappe.query_builder import Case
	from frappe.query_builder.functions import Extract
	from pypika.enums import DatePart

	invoice = frappe.qb.DocType("Sales Invoice")
	year = Extract(DatePart.year, invoice.posting_date)
	month = Extract(DatePart.month, invoice.posting_date)
	bill = invoice.is_return == 0
	total = Case().when(invoice.rounded_total != 0, invoice.rounded_total).else_(invoice.grand_total)

	def of_bills(value):
		return Sum(Case().when(bill, value).else_(0))

	query = (
		frappe.qb.from_(invoice)
		.select(
			year.as_("year"),
			month.as_("month"),
			of_bills(1).as_("bills"),
			of_bills(invoice.net_total).as_("before_gst"),
			of_bills(invoice.total_taxes_and_charges).as_("gst"),
			of_bills(total).as_("total"),
			of_bills(invoice.outstanding_amount).as_("still_due"),
			Sum(Case().when(bill, 0).else_(-total)).as_("credited"),
		)
		.where(
			(invoice.company == get_settings().billing_company)
			& invoice.compliance_client.isnotnull()
			& (invoice.docstatus == 1)
			& invoice.posting_date.between(from_date, to_date)
		)
		.where(scoped.where(invoice))
		.groupby(year, month)
		.orderby(year)
		.orderby(month)
	)
	if client:
		query = query.where(invoice.compliance_client == client)
	rows = query.run(as_dict=True)
	for row in rows:
		row.month_name = format_date(date(int(row.year), int(row.month), 1), "MMM yyyy")
		row.bills = int(row.bills or 0)
		row.settled = flt(flt(row.total) - flt(row.still_due), 2)
	return rows


def unbilled_for_clients(client: str | None) -> list[dict]:
	"""Filed returns with a price on no bill yet, for one client or every client that has not left."""
	clients = (
		[client]
		if client
		else scoped.get_all("Compliance Client", filters={"status": ("!=", "Left")}, pluck="name")
	)
	return sorted(unbilled_for(clients), key=lambda row: (row.client_name, str(row.filed_on or ""), row.name))


def state_with_code(state: str | None) -> str:
	"""Karnataka (29): a state as bills write the place of supply."""
	codes = {name: code for code, name in GST_STATE_CODES.items()}
	return f"{state} ({codes[state]})" if state in codes else state or ""


def upi_qr(upi_id: str | None, payee: str, amount: float, note: str) -> str | None:
	"""A QR code to pay `amount` by UPI, as an SVG data address for the printed bill."""
	if not upi_id or amount <= 0:
		return None
	import base64
	import io
	from urllib.parse import urlencode

	import pyqrcode

	address = "upi://pay?" + urlencode(
		{"pa": upi_id, "pn": payee, "am": f"{amount:.2f}", "cu": "INR", "tn": note}
	)
	svg = io.BytesIO()
	pyqrcode.create(address).svg(svg, scale=3, quiet_zone=2, xmldecl=False)
	return "data:image/svg+xml;base64," + base64.b64encode(svg.getvalue()).decode()


def firm_details() -> dict:
	settings = get_settings()
	return frappe._dict(
		name=settings.billing_company,
		gst_status=settings.gst_status or REGISTERED,
		gstin=settings.billing_gstin,
		state=state_with_code(settings.billing_state),
		address=settings.billing_address,
		bank_details=settings.bank_details,
		upi_id=settings.upi_id,
		logo=settings.billing_logo,
	)


def bill_print(bill) -> dict:
	"""What the KlyONIX Bill layout prints beside the invoice itself (a Jinja method, hooks.py)."""
	from frappe.utils import money_in_words

	firm = firm_details()
	client = billing_party(bill.get("compliance_client"), bill.get("billed_company"))
	total = flt(bill.rounded_total or bill.grand_total)
	due = flt(bill.outstanding_amount) if bill.docstatus == 1 else total
	title = bill.get("bill_title") or BILL_TITLES[firm.gst_status]
	credit = bool(bill.get("is_return"))
	against = None
	if credit and bill.return_against:
		against = {
			"name": bill.return_against,
			"date": scoped.get_value("Sales Invoice", bill.return_against, "posting_date"),
		}
	return {
		"title": "Credit Note" if credit else title,
		"credit": credit,
		"against": against,
		"composition_note": _(COMPOSITION_NOTE) if title == BILL_TITLES["Composition"] else "",
		"firm": firm,
		"client": client,
		"place_of_supply": state_with_code(client.billing_state),
		"in_words": money_in_words(abs(total), bill.currency),
		"due": due,
		# A credit note is not paid; nothing to scan.
		"qr": upi_qr(firm.upi_id, firm.name or "", due, bill.name)
		if bill.docstatus != 2 and not credit
		else None,
	}


def receipt_print(entry) -> dict:
	"""What the KlyONIX Receipt layout prints for a payment (a Jinja method, hooks.py)."""
	from frappe.utils import money_in_words

	bills = [row for row in entry.references if row.reference_doctype == "Sales Invoice"]
	client = client_of_payment(entry)
	tds = flt(sum(flt(row.amount) for row in entry.deductions))
	return {
		"firm": firm_details(),
		"client": billing_party(client),
		"bills": [{"name": row.reference_name, "amount": row.allocated_amount} for row in bills],
		"tds": tds,
		"in_words": money_in_words(flt(entry.paid_amount), entry.paid_to_account_currency or "INR"),
	}


def credited_lines(bill: str) -> dict[str, frappe._dict]:
	"""What the bill's sent credit notes have credited on each of its lines: units and amount."""
	row = frappe.qb.DocType("Sales Invoice Item")
	note = frappe.qb.DocType("Sales Invoice")
	rows = (
		frappe.qb.from_(row)
		.join(note)
		.on(note.name == row.parent)
		.select(row.sales_invoice_item, Sum(row.qty).as_("qty"), Sum(row.amount).as_("amount"))
		.where((note.return_against == bill) & (note.is_return == 1) & (note.docstatus == 1))
		.where(scoped.where(row))
		.where(scoped.where(note))
		.groupby(row.sales_invoice_item)
	).run(as_dict=True)
	return {r.sales_invoice_item: frappe._dict(qty=-flt(r.qty), amount=-flt(r.amount)) for r in rows}


def creditable(line, credited: dict) -> tuple[float, float]:
	"""The units of a bill line not yet credited, and what they come to before GST."""
	done = credited.get(line.name)
	if not done:
		return flt(line.qty), flt(line.amount, 2)
	units = flt(line.qty) - done.qty
	return units, flt(line.rate * units, 2) if units > 0 else 0.0


def follow_credits(original: str | None):
	"""A filing's line credited in full frees the filing to be billed again; a credit cancelled
	bills it in the original bill again, unless it has been billed elsewhere since."""
	if not original:
		return
	bill = frappe.get_doc("Sales Invoice", original)
	if bill.docstatus != 1:
		return
	credited = credited_lines(original)
	freed, kept = [], []
	for line in bill.items:
		if not line.get("compliance_task"):
			continue
		done = credited.get(line.name)
		in_full = done and done.amount >= flt(line.amount, 2) - 0.005
		(freed if in_full else kept).append(line.compliance_task)
	task = frappe.qb.DocType("Compliance Task")
	if freed:
		(
			frappe.qb.update(task)
			.set(task.billed_in, None)
			.where(task.name.isin(freed) & (task.billed_in == original))
			.where(scoped.where(task))
		).run()
	if kept:
		(
			frappe.qb.update(task)
			.set(task.billed_in, original)
			.where(task.name.isin(kept) & task.billed_in.isnull())
			.where(scoped.where(task))
		).run()


def credit_note(name: str, reason: str, amount: float | None = None, line: str | None = None) -> str:
	"""A credit note against a sent bill, as ERPNext's own return invoice, lowering what is due:
	- for every line not yet credited, in full;
	- or for one line, in full or for an amount before GST (the GST on it is credited too).

	ERPNext credits each line once at most up to its own rate, so a line credited in part is done.
	A credit is at most what is still due: there is no refund to settle more."""
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

	bill = bill_of(name)
	if bill.docstatus != 1 or bill.is_return:
		frappe.throw(_("Only a sent bill can be credited, not {0}.").format(name))
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Say why {0} is credited.").format(name))
	if amount is not None and not line:
		frappe.throw(_("Choose the line of {0} to credit {1} on.").format(name, amount))
	credited = credited_lines(bill.name)
	open_lines = {row.name: row for row in bill.items if creditable(row, credited)[0] > 0}
	if not open_lines:
		frappe.throw(_("Every line of {0} is credited already.").format(name))
	if line and line not in open_lines:
		frappe.throw(_("That line of {0} is credited already, or is not on it.").format(name))

	note = make_sales_return(bill.name)
	note.billed_company = bill.billed_company  # credited to the company the bill was for
	note.update_outstanding_for_self = 0  # the credit lowers what is due on the bill itself
	note.remarks = reason
	# make_sales_return leaves lines with nothing left to credit at zero; ERPNext refuses those.
	rows = [row for row in note.items if row.sales_invoice_item in open_lines]
	for row in rows:
		units, _left = creditable(open_lines[row.sales_invoice_item], credited)
		row.qty = -units
	if line:
		rows = [row for row in rows if row.sales_invoice_item == line]
		if amount is not None:
			amount = flt(amount, 2)
			units, left = creditable(open_lines[line], credited)
			if amount <= 0 or amount > left:
				frappe.throw(
					_("A credit on this line of {0} is above zero and at most its {1} before GST.").format(
						name, frappe.format(left, {"fieldtype": "Currency"})
					)
				)
			row = rows[0]
			row.rate = flt(amount / units, row.precision("rate"))
			if flt(row.rate * units, 2) != amount:
				frappe.throw(
					_(
						"{0} does not divide evenly over the line's {1} units; credit the line in full."
					).format(amount, units)
				)
			row.description = _("Credit against {0}: {1}").format(bill.name, reason)
	note.items = rows
	# ERPNext weighs the credit against what is due before it totals it again; total it first.
	note.calculate_taxes_and_totals()
	# Credit beyond what is due would leave the firm owing the client, with no refund to settle it.
	credit = abs(flt(note.rounded_total) or flt(note.grand_total))
	if credit > flt(bill.outstanding_amount) + 0.005:
		frappe.throw(
			_("A credit of {0} with GST is more than the {1} still due on {2}.").format(
				frappe.format(credit, {"fieldtype": "Currency"}),
				frappe.format(bill.outstanding_amount, {"fieldtype": "Currency"}),
				name,
			)
		)
	numbering = series(credit=True)
	if numbering:
		note.naming_series = numbering
	note.insert()
	note.submit()
	return note.name


def credit_notes_of(bill: str) -> list[dict]:
	return scoped.get_all(
		"Sales Invoice",
		filters={"return_against": bill, "is_return": 1, "docstatus": 1},
		fields=["name", "posting_date", "grand_total", "remarks"],
		order_by="posting_date asc, name asc",
	)


def write_off(name: str, reason: str) -> str:
	"""Write off what is still due on a sent bill (a small balance the client will not pay), as a
	journal entry to the company's write-off account against the bill."""
	bill = bill_of(name)
	due = flt(bill.outstanding_amount, 2)
	if bill.docstatus != 1 or due <= 0:
		frappe.throw(_("{0} has nothing still due to write off.").format(name))
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Say why what is left on {0} is written off.").format(name))
	company = scoped.get_value("Company", bill.company, ["write_off_account", "cost_center"], as_dict=True)
	if not company.write_off_account:
		frappe.throw(_("{0} has no write-off account set.").format(bill.company))
	entry = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"voucher_type": "Write Off Entry",
			"company": bill.company,
			"posting_date": nowdate(),
			"user_remark": _("Written off: {0}").format(reason),
			"accounts": [
				{
					"account": bill.debit_to,
					"party_type": "Customer",
					"party": bill.customer,
					"credit_in_account_currency": due,
					"reference_type": "Sales Invoice",
					"reference_name": bill.name,
					"cost_center": company.cost_center,
				},
				{
					"account": company.write_off_account,
					"debit_in_account_currency": due,
					"cost_center": company.cost_center,
				},
			],
		}
	)
	entry.insert()
	entry.submit()
	return entry.name


def written_off(bill: str) -> list[dict]:
	account = frappe.qb.DocType("Journal Entry Account")
	entry = frappe.qb.DocType("Journal Entry")
	return (
		frappe.qb.from_(account)
		.join(entry)
		.on(entry.name == account.parent)
		.select(
			entry.name,
			entry.posting_date,
			account.credit_in_account_currency.as_("amount"),
			entry.user_remark,
		)
		.where(
			(account.reference_type == "Sales Invoice")
			& (account.reference_name == bill)
			& (entry.voucher_type == "Write Off Entry")
			& (entry.docstatus == 1)
		)
		.where(scoped.where(account))
		.where(scoped.where(entry))
	).run(as_dict=True)


def record_advance(
	client: str,
	amount: float,
	paid_on: str,
	mode: str,
	reference: str | None = None,
	paid_by: str | None = None,
) -> str:
	"""Money a client pays before it is billed, kept as an advance and used against its next bills,
	whichever of its companies they are for."""
	from erpnext.accounts.party import get_party_account

	check_biller()
	paid_by = payer(client, paid_by)
	amount = flt(amount, 2)
	if amount <= 0:
		frappe.throw(_("An advance is an amount above zero."))
	if getdate(paid_on) > getdate(nowdate()):
		frappe.throw(_("A payment cannot be dated {0}, after today.").format(format_date(paid_on)))
	if mode not in PAYMENT_MODES:
		frappe.throw(_("Pay by one of {0}, not {1}.").format(", ".join(PAYMENT_MODES), mode))
	company = get_settings().billing_company
	customer = customer_for(client)
	entry = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"payment_type": "Receive",
			"party_type": "Customer",
			"party": customer,
			"company": company,
			"posting_date": getdate(paid_on),
			"paid_from": get_party_account("Customer", customer, company),
			"paid_to": payment_account(company, mode),
			"paid_amount": amount,
			"received_amount": amount,
			"mode_of_payment": mode,
			"reference_no": (reference or "").strip() or mode,
			"reference_date": getdate(paid_on),
			"remarks": _("Advance from {0}").format(paid_by or client_title(client)),
			"paid_by_company": paid_by,
		}
	)
	entry.insert()
	entry.submit()
	return entry.name


def advance_held(customer: str | None) -> float:
	"""What a client has paid ahead and not yet had used against a bill."""
	if not customer:
		return 0
	entry = frappe.qb.DocType("Payment Entry")
	held = (
		frappe.qb.from_(entry)
		.select(Sum(entry.unallocated_amount))
		.where(
			(entry.party_type == "Customer")
			& (entry.party == customer)
			& (entry.company == get_settings().billing_company)
			& (entry.docstatus == 1)
		)
		.where(scoped.where(entry))
	).run()[0][0]
	return flt(held)


def payments(client: str | None, text: str | None, start: int, limit: int) -> dict:
	"""One page of the payments the firm has received, newest first, with each one's client, TDS
	and the bills it settled; and how many there are and how much they came to."""
	check_biller()
	filters = [
		["company", "=", get_settings().billing_company],
		["payment_type", "=", "Receive"],
		["party_type", "=", "Customer"],
		["docstatus", "=", 1],
	]
	if client:
		check_client_allowed(client)
		filters.append(["party", "=", scoped.get_value("Compliance Client", client, "customer") or ""])
	elif billable_clients() is not None:
		customers = scoped.get_all(
			"Compliance Client",
			filters={"name": ("in", list(billable_clients()) or [""])},
			pluck="customer",
		)
		filters.append(["party", "in", [name for name in customers if name] or [""]])
	text = (text or "").strip()
	matching = (
		[
			["name", "like", f"%{text}%"],
			["party_name", "like", f"%{text}%"],
			["reference_no", "like", f"%{text}%"],
		]
		if text
		else None
	)
	rows = frappe.get_list(
		"Payment Entry",
		filters=filters,
		or_filters=matching,
		fields=[
			"name",
			"posting_date",
			"party",
			"party_name",
			"paid_by_company",
			"mode_of_payment",
			"reference_no",
			"paid_amount",
			"unallocated_amount",
			"total_allocated_amount",
		],
		order_by="posting_date desc, name desc",
		start=start,
		page_length=limit,
	)
	totals = frappe.get_list(
		"Payment Entry",
		filters=filters,
		or_filters=matching,
		fields=[{"COUNT": "*", "as": "count"}, {"SUM": "paid_amount", "as": "received"}],
	)
	names = [row.name for row in rows]
	client_of = {
		row.customer: row
		for row in scoped.get_all(
			"Compliance Client",
			filters={"customer": ("in", [row.party for row in rows] or [""])},
			fields=["customer", "name", "client_name"],
		)
	}
	bills: dict[str, list[str]] = {}
	for ref in scoped.get_all(
		"Payment Entry Reference",
		filters={"parent": ("in", names or [""]), "reference_doctype": "Sales Invoice"},
		fields=["parent", "reference_name"],
	):
		bills.setdefault(ref.parent, []).append(ref.reference_name)
	for row in rows:
		owner = client_of.get(row.party)
		row.client = owner.name if owner else None
		row.client_name = owner.client_name if owner else None
		row.bills = bills.get(row.name, [])
		row.tds = flt(row.total_allocated_amount - (row.paid_amount - row.unallocated_amount), 2)
	return {
		"rows": rows,
		"total": totals[0]["count"] if totals else 0,
		"received": flt(totals[0]["received"]) if totals else 0,
		"modes": list(PAYMENT_MODES),
	}


def reminder_steps(text: str | None) -> list[int]:
	"""The days late to remind on, from "3, 15, 30"; each once, in order."""
	days = set()
	for part in (text or "3, 15, 30").replace(";", ",").split(","):
		part = part.strip()
		if part.isdigit() and int(part) > 0:
			days.add(int(part))
	return sorted(days)


def send_overdue_reminders(today: date | None = None):
	"""Daily: a client whose bill is late is emailed it again, on the latest step it has reached
	(days late), once per step; nothing once it is paid."""
	from kxcompliance.kx_compliance.reminders import already_sent, write_log

	settings = get_settings()
	if settings.account_type != FIRM or not settings.billing_company or not settings.overdue_reminders:
		return
	today = getdate(today or nowdate())
	steps = reminder_steps(settings.reminder_steps)
	late = scoped.get_all(
		"Sales Invoice",
		filters={
			"company": settings.billing_company,
			"compliance_client": ("is", "set"),
			"docstatus": 1,
			"is_return": 0,
			"outstanding_amount": (">", 0),
			"due_date": ("<", today),
		},
		fields=["name", "due_date"],
	)
	due = []
	for row in late:
		reached = [day for day in steps if (today - getdate(row.due_date)).days >= day]
		if reached:
			due.append((row, reached[-1], f"{row.name}|overdue|{reached[-1]}"))
	sent = already_sent([key for _row, _day, key in due])
	for row, day, key in due:
		if key in sent:
			continue
		savepoint = "overdue_reminder"
		frappe.db.savepoint(savepoint)
		try:
			bill = frappe.get_doc("Sales Invoice", row.name)
			to = email_bill(bill, overdue_days=day)
			if to:
				write_log("Reminder", key, [to], rule_days=day, due_date=row.due_date, sales_invoice=row.name)
		except Exception:
			frappe.db.rollback(save_point=savepoint)
			frappe.log_error(title=f"Overdue reminder for {row.name} could not be sent")
