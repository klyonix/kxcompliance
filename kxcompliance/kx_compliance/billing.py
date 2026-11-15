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
from frappe.utils import add_days, add_months, flt, format_date, get_first_day, getdate, nowdate

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
# A filing is billed once it is filed (compliance_task.FILED_STATUSES).
BILLABLE_STATUSES = ("Filed", "Filed Late")
WITHOUT_GST = "Without GST"
# Who may open billing in the app at all; making, sending and cancelling bills is then ERPNext's
# own right to Sales Invoices (Accounts User or Manager), which its accounting checks need too.
BILLING_ROLES = frozenset({"System Manager", "Compliance Manager", "Accounts Manager", "Accounts User"})
# A bill is due this many days after it is made.
BILL_DUE_DAYS = 15
FEE_MONTHS = {"Monthly": 1, "Quarterly": 3, "Yearly": 12}
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
	return {
		"company": settings.billing_company,
		**{field: settings.get(field) or "" for field in FIRM_FIELDS},
		"states": [state for state in states.split("\n") if state],
		"can_create_company": bool(frappe.has_permission("Company", "create")) and frappe.is_setup_complete(),
		"return_fees": [
			{"obligation_template": row.obligation_template, "amount": row.amount}
			for row in settings.return_fees
		],
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
	# Government fees passed on carry no GST: their item is taxed at nothing on every GST account.
	without = item_tax_template(company, list(accounts.values()))
	item = frappe.get_doc("Item", GOVERNMENT_FEES_ITEM)
	if without not in [row.item_tax_template for row in item.taxes]:
		item.append("taxes", {"item_tax_template": without})
		item.save()
	# Payments: into cash or the firm's bank, and TDS the client deducts, kept as an asset.
	bank = bank_ledger(company)
	cash = frappe.db.get_value("Company", company, "default_cash_account")
	for mode, kind in PAYMENT_MODES.items():
		payment_mode(mode, kind, company, cash if kind == "Cash" else bank)
	ledger(company, TDS_ACCOUNT, "Tax Assets")


def ledger(company: str, name: str, parent_name: str, account_type: str | None = None) -> str:
	"""An account under one of the company's groups, made only if it is not there."""
	existing = frappe.db.get_value("Account", {"company": company, "account_name": name, "is_group": 0})
	if existing:
		return existing
	parent = frappe.db.get_value("Account", {"company": company, "account_name": parent_name, "is_group": 1})
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
	bank = frappe.db.get_value("Company", company, "default_bank_account")
	if bank:
		return bank
	bank = ledger(company, "Bank", "Bank Accounts", "Bank")
	# ERPNext keeps the company's default bank on the company; the app sets only this, once.
	frappe.db.set_value("Company", company, "default_bank_account", bank)
	return bank


def payment_mode(mode: str, kind: str, company: str, account: str):
	"""A way of paying, which pays into this account for the company."""
	if not frappe.db.exists("Mode of Payment", mode):
		frappe.get_doc({"doctype": "Mode of Payment", "mode_of_payment": mode, "type": kind}).insert()
	doc = frappe.get_doc("Mode of Payment", mode)
	if not any(row.company == company for row in doc.accounts):
		doc.append("accounts", {"company": company, "default_account": account})
		doc.save()


def item_tax_template(company: str, accounts: list[str]) -> str:
	existing = frappe.db.get_value("Item Tax Template", {"company": company, "title": WITHOUT_GST})
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


def check_return_fees(rows, where: str):
	"""Each return priced once, from the library."""
	seen = set()
	for row in rows:
		if row.obligation_template in seen:
			frappe.throw(
				_("{0} row {1}: {2} already has a price.").format(where, row.idx, row.obligation_template)
			)
		seen.add(row.obligation_template)


def check_fee_plan(client):
	"""A fixed fee says how often it is billed and from when."""
	if not client.fixed_fee:
		client.fee_frequency = None
		client.fee_from = None
		return
	missing = [
		_(client.meta.get_label(field)) for field in ("fee_frequency", "fee_from") if not client.get(field)
	]
	if missing:
		frappe.throw(
			_("{0} has a fixed fee of {1}; give {2} too.").format(
				client.name or client.client_name, client.fixed_fee, ", ".join(missing)
			)
		)


def unbilled_filings(client: str) -> list[dict]:
	"""The client's filings that are filed, have a fee and are on no bill yet (sent or draft),
	oldest first."""
	return unbilled_for([client])


def unbilled_for(clients: list[str]) -> list[dict]:
	"""Filed returns with a fee that are on no bill yet (sent or draft), for these clients, oldest
	first; each with its client and fee. Read in a few queries however many clients there are."""
	if not clients:
		return []
	owner = dict(
		frappe.get_all(
			"Company Compliance Profile",
			filters={"client": ("in", clients)},
			fields=["company", "client"],
			as_list=True,
		)
	)
	firm_prices = {row.obligation_template: row.amount for row in get_settings().return_fees}
	own_prices: dict[str, dict[str, float]] = {}
	for row in frappe.get_all(
		"Return Fee",
		filters={"parenttype": "Compliance Client", "parent": ("in", clients)},
		fields=["parent", "obligation_template", "amount"],
	):
		own_prices.setdefault(row.parent, {})[row.obligation_template] = row.amount
	if not owner or not (firm_prices or own_prices):
		return []
	rows = frappe.get_all(
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
	found = []
	for row in rows:
		row.client = owner[row.company]
		row.fee = own_prices.get(row.client, {}).get(
			row.obligation_template, firm_prices.get(row.obligation_template)
		)
		if row.fee and row.name not in drafted:
			found.append(row)
	return found


def client_fees(client: str) -> dict:
	"""A client's fee plan and what it would be billed for its filings now."""
	values = frappe.db.get_value(
		"Compliance Client", client, ["fixed_fee", "fee_frequency", "fee_from"], as_dict=True
	)
	unbilled = unbilled_filings(client)
	return {
		**values,
		"unbilled": unbilled,
		"unbilled_total": sum(row.fee for row in unbilled),
	}


def save_return_fees(fees: list) -> list[dict]:
	"""The firm's price per return, replacing the list; each row a return and its fee."""
	check_firm_manager()
	settings = frappe.get_doc(SETTINGS)
	settings.set("return_fees", [])
	for fee in fees:
		if not isinstance(fee, dict) or set(fee) - {"obligation_template", "amount"}:
			frappe.throw(_("Each price is a return and its fee."))
		settings.append(
			"return_fees",
			{"obligation_template": fee.get("obligation_template"), "amount": flt(fee.get("amount"))},
		)
	settings.save()
	return [
		{"obligation_template": row.obligation_template, "amount": row.amount} for row in settings.return_fees
	]


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
		if name and frappe.db.exists(doctype, {"name": name, "is_group": 0}):
			return name
	return frappe.db.get_value(doctype, {"is_group": 0})


def customer_for(client: str) -> str:
	"""The client's Customer, made the first time it is billed. A link the app keeps, not a state
	of the client, so it is written directly."""
	values = frappe.db.get_value(
		"Compliance Client", client, ["client_name", "client_kind", "customer", "gstin"], as_dict=True
	)
	if not values:
		frappe.throw(_("Client {0} does not exist.").format(client))
	if values.customer and frappe.db.exists("Customer", values.customer):
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


def tax_template_for(client_state: str | None) -> str | None:
	"""Within the firm's state, CGST and SGST; elsewhere (or not known), IGST."""
	settings = get_settings()
	title = WITHIN_STATE if client_state and client_state == settings.billing_state else OUTSIDE_STATE
	return frappe.db.get_value(
		"Sales Taxes and Charges Template", {"company": settings.billing_company, "title": title}
	)


def series() -> str | None:
	"""The firm's bill numbering, RA/26-27/0001, offered on Sales Invoice; None without a prefix."""
	prefix = (get_settings().bill_prefix or "").strip()
	if not prefix:
		return None
	name = f"{prefix}/.TFY./.####"
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


def fee_period(plan, month: date) -> str | None:
	"""The fixed fee's period starting in this month, as a bill line says it; None when the fee is
	not billed this month."""
	step = FEE_MONTHS.get(plan.fee_frequency)
	if not plan.fixed_fee or not step or not plan.fee_from:
		return None
	start = get_first_day(plan.fee_from)
	gap = (month.year - start.year) * 12 + month.month - start.month
	if gap < 0 or gap % step:
		return None
	first = format_date(month, "MMM yyyy")
	if step == 1:
		return first
	return _("{0} to {1}").format(first, format_date(add_months(month, step - 1), "MMM yyyy"))


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
		).run(pluck=True)
	)


def make_bill(
	client: str,
	filings: list[str] | None = None,
	fee_month: date | None = None,
	lines: list[dict] | None = None,
	key: str | None = None,
) -> str:
	"""A draft bill for a client: the filings chosen (from its unbilled ones), the fixed fee for
	the period starting in `fee_month`, and any other lines ({description, amount, government})."""
	settings = get_settings()
	unbilled = {row.name: row for row in unbilled_filings(client)}
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
		}
		for name in asked
	]
	plan = frappe.db.get_value(
		"Compliance Client", client, ["fixed_fee", "fee_frequency", "fee_from", "billing_state"], as_dict=True
	)
	period = fee_period(plan, fee_month) if fee_month else None
	if period:
		items.append(
			{
				"item_code": FEES_ITEM,
				"description": _("Fixed fee, {0}").format(period),
				"qty": 1,
				"rate": plan.fixed_fee,
			}
		)
	for line in lines or []:
		items.append(other_line(line))
	if not items:
		frappe.throw(
			_("Nothing to bill {0} for: choose filings, the fixed fee or add a line.").format(client)
		)
	today = getdate(nowdate())
	template = tax_template_for(plan.billing_state)
	bill = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": settings.billing_company,
			"customer": customer_for(client),
			"compliance_client": client,
			"kx_billing_key": key,
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


def other_line(line: dict) -> dict:
	"""A typed line: a description and amount; government fees go on the item without GST."""
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
	}


def bill_of(name: str):
	"""One of the firm's bills, for those who bill; never another company's invoice."""
	check_biller()
	bill = frappe.get_doc("Sales Invoice", name)
	bill.check_permission("read")
	if bill.company != get_settings().billing_company or not bill.compliance_client:
		frappe.throw(_("{0} is not one of the firm's bills.").format(name), frappe.PermissionError)
	return bill


def send_bill(name: str) -> dict:
	"""Submit a draft bill, so it is in the books, then email it to the client."""
	bill = bill_of(name)
	if bill.docstatus != 0:
		frappe.throw(_("{0} has been sent already.").format(name))
	bill.submit()
	return {"name": bill.name, "emailed_to": email_bill(bill)}


def email_bill(bill) -> str | None:
	"""Email the bill's PDF to the client's billing email, else its contact; the address, or None."""
	from kxcompliance.kx_compliance.reminders import sender_address

	address = frappe.db.get_value(
		"Compliance Client", bill.compliance_client, ["billing_email", "contact_email"], as_dict=True
	)
	to = address.billing_email or address.contact_email
	sender = sender_address()
	if not to or not sender:
		return None
	frappe.sendmail(
		recipients=[to],
		sender=sender,
		subject=_("Bill {0} from {1}").format(bill.name, bill.company),
		message=_("Please find bill {0} for {1} attached, due on {2}.").format(
			bill.name, frappe.format(bill.grand_total, {"fieldtype": "Currency"}), format_date(bill.due_date)
		),
		attachments=[frappe.attach_print("Sales Invoice", bill.name, file_name=bill.name.replace("/", "-"))],
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
	"""A sent bill: its filings are billed in it, each only once."""
	filings = [row.compliance_task for row in bill.items if row.get("compliance_task")]
	if not filings:
		return
	task = frappe.qb.DocType("Compliance Task")
	elsewhere = (
		frappe.qb.from_(task)
		.select(task.name, task.billed_in)
		.where(task.name.isin(filings) & task.billed_in.isnotnull() & (task.billed_in != bill.name))
	).run(as_dict=True)
	if elsewhere:
		frappe.throw(_("{0} is already billed in {1}.").format(elsewhere[0].name, elsewhere[0].billed_in))
	# A link kept by the bill's own submit, not a state of the filing.
	(frappe.qb.update(task).set(task.billed_in, bill.name).where(task.name.isin(filings))).run()


def unmark_filings_billed(bill, method=None):
	"""A cancelled bill: its filings may be billed again."""
	task = frappe.qb.DocType("Compliance Task")
	(frappe.qb.update(task).set(task.billed_in, None).where(task.billed_in == bill.name)).run()


def make_monthly_drafts(today: date | None = None):
	"""On the 1st: a draft bill per client with its fixed fee due or filed returns to bill, for a
	manager to check and send. Made once per client and month; one client's problem stops no other."""
	settings = get_settings()
	if settings.account_type != FIRM or not settings.billing_company:
		return
	month = get_first_day(today or nowdate())
	for client in frappe.get_all("Compliance Client", filters={"status": ("!=", "Left")}, pluck="name"):
		key = f"{client}|{month.isoformat()[:7]}"
		if frappe.db.exists("Sales Invoice", {"kx_billing_key": key, "docstatus": ("!=", 2)}):
			continue
		try:
			filings = [row.name for row in unbilled_filings(client)]
			plan = frappe.db.get_value(
				"Compliance Client", client, ["fixed_fee", "fee_frequency", "fee_from"], as_dict=True
			)
			if filings or fee_period(plan, month):
				make_bill(client, filings=filings, fee_month=month, key=key)
			# A job may commit as it goes, so a later client's problem loses nothing made before it.
			frappe.db.commit()
		except Exception:
			# A scheduled job: undo this client's half-made bill, keep the others, and say why.
			frappe.db.rollback()
			frappe.log_error(title=f"Monthly bill for {client} could not be made")


def bill_options(client: str) -> dict:
	"""What a new bill for a client may hold: its unbilled filings, and its fixed fee if one falls
	due this month."""
	check_biller()
	month = get_first_day(nowdate())
	plan = frappe.db.get_value(
		"Compliance Client", client, ["fixed_fee", "fee_frequency", "fee_from"], as_dict=True
	)
	return {
		"filings": unbilled_filings(client),
		"fixed_fee": plan.fixed_fee or 0,
		"fee_period": fee_period(plan, month),
	}


BILL_FIELDS = (
	"name",
	"compliance_client",
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
)


def bill_detail(name: str) -> dict:
	"""A bill as its page shows it: lines, tax, totals, what is due."""
	bill = bill_of(name)
	return {
		**{field: bill.get(field) for field in BILL_FIELDS},
		"items": [
			{"description": row.description, "amount": row.amount, "filing": row.get("compliance_task")}
			for row in bill.items
		],
		"taxes": [{"description": row.description, "amount": row.tax_amount} for row in bill.taxes],
		"payments": payments_of(bill.name) if bill.docstatus == 1 else [],
		"modes": list(PAYMENT_MODES),
	}


def record_payment(
	name: str, amount: float, paid_on: str, mode: str, reference: str | None = None, tds: float = 0
) -> str:
	"""A payment against a sent bill, in full or in part, as ERPNext's own Payment Entry from the
	bill. TDS the client deducted is recorded beside it, so the bill is settled by both."""
	bill = bill_of(name)
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

	account = frappe.db.get_value(
		"Mode of Payment Account", {"parent": mode, "company": bill.company}, "default_account"
	)
	entry = get_payment_entry("Sales Invoice", bill.name, party_amount=amount)
	entry.posting_date = getdate(paid_on)
	entry.mode_of_payment = mode
	if account:
		entry.paid_to = account
	entry.paid_amount = entry.received_amount = amount
	entry.reference_no = (reference or "").strip() or mode
	entry.reference_date = getdate(paid_on)
	for row in entry.references:
		row.allocated_amount = amount + tds
	if tds:
		entry.append(
			"deductions",
			{
				"account": frappe.db.get_value(
					"Account", {"company": bill.company, "account_name": TDS_ACCOUNT, "is_group": 0}
				),
				"cost_center": frappe.db.get_value("Company", bill.company, "cost_center"),
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
		.orderby(entry.posting_date)
		.orderby(entry.name)
	).run(as_dict=True)
	for row in rows:
		row.tds = flt(row.allocated_amount - row.paid_amount, 2)
	return rows


def cancel_payment(name: str):
	"""Cancel a payment recorded against one of the firm's bills; the bill is due again."""
	entry = frappe.get_doc("Payment Entry", name)
	bills = [row.reference_name for row in entry.references if row.reference_doctype == "Sales Invoice"]
	if not bills:
		frappe.throw(_("{0} is not a payment against one of the firm's bills.").format(name))
	bill_of(bills[0])  # who may bill, and a bill of the firm's
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
	"customer_name",
	"posting_date",
	"due_date",
	"grand_total",
	"rounded_total",
	"outstanding_amount",
	"docstatus",
	"status",
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
		filters.append(["compliance_client", "=", client])
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
	company = get_settings().billing_company
	if not company:
		return {"bills": [], "outstanding": 0, "overdue": 0}
	sent = {"company": company, "compliance_client": client, "docstatus": 1}
	shown = sent if own else {**sent, "docstatus": ("in", (0, 1))}
	bills_shown = frappe.get_all(
		"Sales Invoice", filters=shown, fields=LIST_FIELDS, order_by="posting_date desc, name desc", limit=10
	)
	due = frappe.get_all(
		"Sales Invoice",
		filters={**sent, "outstanding_amount": (">", 0)},
		fields=["outstanding_amount", "due_date"],
	)
	today = getdate(nowdate())
	result = {
		"bills": bills_shown,
		"outstanding": sum(flt(row.outstanding_amount) for row in due),
		"overdue": sum(flt(row.outstanding_amount) for row in due if getdate(row.due_date) < today),
	}
	if not own:
		unbilled = unbilled_filings(client)
		result["unbilled_count"] = len(unbilled)
		result["unbilled_total"] = sum(row.fee for row in unbilled)
	return result


# How late a bill is, by days past its due date: the columns of Billing Outstanding.
AGEING = (
	("not_due", None, 0),
	("late_30", 1, 30),
	("late_60", 31, 60),
	("late_90", 61, 90),
	("late_more", 91, None),
)


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
	return sorted(clients.values(), key=lambda line: (-line["late_more"], -line["outstanding"]))


def billing_by_month(from_date, to_date, client: str | None) -> list[dict]:
	"""The firm's sent bills month by month: how many, before GST, GST, total, received, still due."""
	from frappe.query_builder.functions import Count, Extract, Sum
	from pypika.enums import DatePart

	invoice = frappe.qb.DocType("Sales Invoice")
	year = Extract(DatePart.year, invoice.posting_date)
	month = Extract(DatePart.month, invoice.posting_date)
	query = (
		frappe.qb.from_(invoice)
		.select(
			year.as_("year"),
			month.as_("month"),
			Count(invoice.name).as_("bills"),
			Sum(invoice.net_total).as_("before_gst"),
			Sum(invoice.total_taxes_and_charges).as_("gst"),
			Sum(invoice.grand_total).as_("total"),
			Sum(invoice.outstanding_amount).as_("still_due"),
		)
		.where(
			(invoice.company == get_settings().billing_company)
			& invoice.compliance_client.isnotnull()
			& (invoice.docstatus == 1)
			& invoice.posting_date.between(from_date, to_date)
		)
		.groupby(year, month)
		.orderby(year)
		.orderby(month)
	)
	if client:
		query = query.where(invoice.compliance_client == client)
	rows = query.run(as_dict=True)
	for row in rows:
		row.month_name = format_date(date(int(row.year), int(row.month), 1), "MMM yyyy")
		row.received = flt(row.total) - flt(row.still_due)
	return rows


def unbilled_for_clients(client: str | None) -> list[dict]:
	"""Filed returns with a price on no bill yet, for one client or every client that has not left."""
	clients = (
		[client]
		if client
		else frappe.get_all("Compliance Client", filters={"status": ("!=", "Left")}, pluck="name")
	)
	return sorted(unbilled_for(clients), key=lambda row: (row.client, str(row.filed_on or ""), row.name))
