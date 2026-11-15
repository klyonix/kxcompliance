# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Whitelisted methods for the KlyONIX Compliance app at /compliance."""

from mimetypes import guess_type

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
from frappe.handler import ALLOWED_MIMETYPES
from frappe.query_builder.functions import Count
from frappe.utils import add_days, cint, get_datetime, getdate, now_datetime, nowdate

from kxcompliance.install import CLIENT_ROLE
from kxcompliance.kx_compliance import (
	app_settings,
	billing,
	clients,
	companies,
	document_requests,
	getting_started,
	month_calendar,
	onboarding,
	people,
	privacy,
	score,
	setup_import,
	tours,
)
from kxcompliance.kx_compliance.company_events import event_types_for
from kxcompliance.kx_compliance.overview import get_overview
from kxcompliance.kx_compliance.party_licences import (
	DOCUMENTS,
	GROUP_FIELDS,
	is_valid_on,
	licence_gap,
	party_licence_items,
	requirements_for_party,
)
from kxcompliance.kx_compliance.register import CLOSED_TASK_STATUSES, compliance_companies, is_approver
from kxcompliance.kx_compliance.search import CANDIDATES as SEARCH_CANDIDATES
from kxcompliance.kx_compliance.search import MIN_LENGTH as SEARCH_MIN_LENGTH
from kxcompliance.kx_compliance.search import counts as search_record_counts
from kxcompliance.kx_compliance.search import like as search_like
from kxcompliance.kx_compliance.search import search as search_records
from kxcompliance.kx_compliance.search import words_of as search_words

APP_ROLES = frozenset({"System Manager", "Compliance Manager", "Compliance User", "Compliance Auditor"})
# People who sell or buy may open the app for the Licence Check only, for their side of the business.
CHECK_ROLES = {"Sales User": "Customer", "Purchase User": "Supplier"}
PARTY_NAME_FIELDS = {"Customer": "customer_name", "Supplier": "supplier_name"}
PARTY_SEARCH_LIMIT = 20
# The most rows one page of a list may ask for (the largest page size offered).
MAX_PAGE_LENGTH = 100
# What a client's login searches: the records it can open in the app.
CLIENT_SEARCH_KINDS = ("items", "filings", "cases", "trademarks", "signatories", "requests")
NAMES_LIMIT = 50
WORK_HORIZON_DAYS = 30
WORK_LIMIT = 200
# Filings that can still be filed or reviewed in bulk, and how many return-and-period choices to offer.
BULK_STATUSES = ("Open", "In Progress", "Ready for Review")
BULK_CHOICES_LIMIT = 100
# The obligation screen's choices, read from the template's own select fields.
OBLIGATION_CHOICES = ("law", "frequency", "period_basis", "registration_type")

# The only fields the app may change on each record; everything else stays in the Desk.
# Who looks after a record is a manager's to change; the record's other fields are its people's.
PEOPLE_FIELDS = ("responsible", "reviewer")
# What a field may be set to through save_changes: never a list or dict.
PLAIN_VALUES = (str, int, float, type(None))

EDITABLE_FIELDS = {
	# Validity dates and the holder stay with renewals and the item's own form, which check them.
	"Compliance Item": (
		"certificate",
		"reference_number",
		"notes",
		"title",
		"issuing_authority",
		"issue_date",
		"valid_from",
		"state",
		"dsc_class",
		"dsc_purpose",
		"certifying_authority",
		"token_serial",
		*PEOPLE_FIELDS,
	),
	# Status, dates and amounts move with hearings and outcomes, and the amounts are managers' only.
	"Legal Case": (
		"title",
		"case_type",
		"forum",
		"forum_name",
		"bench",
		"case_number",
		"cnr_number",
		"notice_reference",
		"state",
		"filing_date",
		"our_role",
		"opposing_party",
		"advocate_contact",
		"summary",
		"outcome",
		# Managers' only (permission level 1); offered and accepted only for those who may write them.
		"risk",
		"amount_involved",
		"provision",
		*PEOPLE_FIELDS,
	),
	"Trademark": (
		"mark",
		"mark_type",
		"application_number",
		"filing_date",
		"user_claim",
		"used_since",
		"examination_report_on",
		"journal_number",
		"journal_date",
		"opposition_notice_on",
		"opposition_number",
		"registration_number",
		"registration_date",
		"notes",
		*PEOPLE_FIELDS,
	),
	"Compliance Task": (
		"status",
		"filed_on",
		"acknowledgement_number",
		"proof",
		"amount_paid",
		"interest",
		"late_fee",
		"remarks",
		*PEOPLE_FIELDS,
	),
	# A scheduled date may also be moved; one with an outcome may not (the doctype checks).
	# While it is open; the doctype refuses changes once it is accepted or withdrawn.
	"Document Request": ("title", "details", "due_date"),
	"Legal Date": ("status", "attended_by", "proceedings", "order", "next_date", "date", "time", "purpose"),
	# Approving moves the item's dates and certificate; the renewal's own rules decide who may.
	"Compliance Renewal": (
		"status",
		"applied_on",
		"application_reference",
		"new_valid_from",
		"new_valid_until",
		"new_certificate",
		"fee",
		"notes",
	),
}


def has_app_access(user: str | None = None) -> bool:
	return bool(APP_ROLES & set(frappe.get_roles(user)))


def party_types_to_check(user: str | None = None) -> list[str]:
	"""Whose licences the person may check: both sides for compliance roles, else by Sales or Purchase User."""
	roles = set(frappe.get_roles(user))
	if APP_ROLES & roles:
		return list(PARTY_NAME_FIELDS)
	return [party_type for role, party_type in CHECK_ROLES.items() if role in roles]


def is_client_login(user: str | None = None) -> bool:
	"""Someone at a firm's client, who signs in to see their companies and upload documents."""
	return CLIENT_ROLE in frappe.get_roles(user) and not has_app_access(user)


def can_open_app(user: str | None = None) -> bool:
	return has_app_access(user) or is_client_login(user) or bool(party_types_to_check(user))


def check_party_type(party_type: str):
	if frappe.session.user == "Guest" or party_type not in party_types_to_check():
		frappe.throw(
			_("You cannot check the licences of a {0}.").format(_(party_type)), frappe.PermissionError
		)


def check_app_access():
	if frappe.session.user == "Guest" or not has_app_access():
		frappe.throw(_("You do not have access to the compliance app."), frappe.PermissionError)


def check_manager_access(message: str):
	check_app_access()
	if not is_approver():
		frappe.throw(message, frappe.PermissionError)


def select_options(meta, fieldname: str) -> list[str]:
	return [option for option in (meta.get_field(fieldname).options or "").split("\n") if option]


def check_reader_access():
	"""For what a client's login may also read: the firm's staff, or the client's own people."""
	if frappe.session.user == "Guest" or not (has_app_access() or is_client_login()):
		frappe.throw(_("You do not have access to the compliance app."), frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def my_work(companies: str | None = None) -> dict:
	"""What the signed-in person holds or reviews and should look at now, soonest first.

	`companies` (the client filter, a JSON list) narrows it to one client's before the limit, so
	a busy person still sees all of that client's work. `limited` says a list reached the limit.
	"""
	check_app_access()
	user = frappe.session.user
	mine = {"responsible": user, "reviewer": user}
	horizon = add_days(nowdate(), WORK_HORIZON_DAYS)
	chosen = company_list(companies)
	within = {"company": ("in", chosen or [""])} if chosen is not None else {}
	work = {
		"items": frappe.get_list(
			"Compliance Item",
			filters={
				"status": (
					"in",
					["Due for Renewal", "Renewal Planned", "Expired", "Lapsed", "Renewal in Progress"],
				),
				**within,
			},
			or_filters=mine,
			fields=[
				"name",
				"title",
				"item_type",
				"status",
				"valid_until",
				"company",
				"responsible",
				"reviewer",
			],
			order_by="valid_until asc",
			limit=WORK_LIMIT,
		),
		"tasks": frappe.get_list(
			"Compliance Task",
			filters={
				"status": ("not in", CLOSED_TASK_STATUSES),
				"effective_due_date": ("<=", horizon),
				**within,
			},
			or_filters=mine,
			fields=[
				"name",
				"obligation_template",
				"period_label",
				"company",
				"status",
				"is_overdue",
				"effective_due_date",
				"responsible",
				"reviewer",
			],
			order_by="effective_due_date asc",
			limit=WORK_LIMIT,
		),
		"legal_dates": frappe.get_list(
			"Legal Date",
			filters={"status": "Scheduled", "date": ("<=", horizon), **within},
			or_filters=mine,
			fields=[
				"name",
				"kind",
				"date",
				"reference_doctype",
				"reference_name",
				"reference_title",
				"company",
				"is_overdue",
			],
			order_by="date asc",
			limit=WORK_LIMIT,
		),
	}
	return {
		**work,
		"limited": any(len(rows) >= WORK_LIMIT for rows in work.values()),
		"as_of": str(now_datetime()),
	}


@frappe.whitelist(methods=["GET"])
def overview(companies: str | None = None) -> dict:
	"""The managers' numbers across the register, filings, legal work and party licences.

	`companies`, a JSON list of company names, narrows them to one client's (the client filter);
	none means every company. A GET request carries it as text, so it is read and checked here.
	"""
	check_app_access()
	if not is_approver():
		frappe.throw(_("Only a Compliance Manager can open the overview."), frappe.PermissionError)
	return get_overview(company_list(companies))


def company_list(companies: str | None) -> list[str] | None:
	"""The client filter's companies from a GET request's text: a list of names, or None for all."""
	chosen = frappe.parse_json(companies) if companies else None
	if chosen is not None and not (
		isinstance(chosen, list) and all(isinstance(name, str) for name in chosen)
	):
		frappe.throw(_("Companies must be a list of company names."), frappe.ValidationError)
	return chosen


@frappe.whitelist(methods=["POST"])
def save_changes(doctype: str, name: str, values: dict, base_modified: str | None = None) -> dict:
	"""Save a few fields on a record, as the app does when online and when sending changes made offline.

	`base_modified` is the record's modified time when the change was made; if the record
	has changed since, the save is refused so nobody else's work is overwritten.
	"""
	check_app_access()
	allowed = EDITABLE_FIELDS.get(doctype)
	if not allowed:
		frappe.throw(_("The app cannot change {0}.").format(_(doctype)), frappe.PermissionError)
	not_allowed = sorted(set(values) - set(allowed))
	if not_allowed:
		frappe.throw(
			_("The app cannot change {0} on {1}.").format(", ".join(not_allowed), _(doctype)),
			frappe.PermissionError,
		)
	not_plain = sorted(field for field, value in values.items() if not isinstance(value, PLAIN_VALUES))
	if not_plain:
		frappe.throw(
			_("{0} on {1} must be a single value, not a list or a table.").format(", ".join(not_plain), name),
			frappe.ValidationError,
		)
	people_changed = {field: values[field] for field in PEOPLE_FIELDS if field in values}
	if people_changed and not is_approver():
		frappe.throw(
			_("Only a Compliance Manager can change who is responsible for or reviews {0}.").format(name),
			frappe.PermissionError,
		)
	team = {person.name for person in onboarding.firm_people()} if people_changed else set()
	for field, user in people_changed.items():
		# The reviewer may be cleared; the responsible person may not, which the doctype enforces.
		if user and user not in team:
			frappe.throw(
				_("{0} cannot be made {1} of {2}: they are not on the team.").format(user, _(field), name),
				frappe.ValidationError,
			)
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")
	# Frappe would quietly keep the old value of a field the person may not write; say so instead.
	locked = sorted(
		field for field in values if not doc.has_permlevel_access_to(field, permission_type="write")
	)
	if locked:
		frappe.throw(
			_("You cannot change {0} on {1}.").format(", ".join(locked), name), frappe.PermissionError
		)
	if base_modified and get_datetime(doc.modified) != get_datetime(base_modified):
		frappe.throw(
			_("{0} {1} was changed by someone else after this change was made.").format(_(doctype), name),
			frappe.TimestampMismatchError,
		)
	doc.update(values)
	doc.save()
	return {"name": doc.name, "modified": str(doc.modified)}


@frappe.whitelist(methods=["GET"])
def editable_fields(doctype: str) -> dict:
	"""The fields the app may change on a record of this type, with each one's label, kind and choices.

	`people` (who can be made responsible or reviewer) is given to managers only, who alone may
	change those fields.
	"""
	check_app_access()
	allowed = EDITABLE_FIELDS.get(doctype)
	if not allowed:
		frappe.throw(_("The app cannot change {0}.").format(_(doctype)), frappe.PermissionError)
	meta = frappe.get_meta(doctype)
	writable_levels = meta.get_permlevel_access("write")
	fields = {}
	for fieldname in allowed:
		field = meta.get_field(fieldname)
		if field.permlevel not in writable_levels:
			continue
		fields[fieldname] = {
			"label": _(field.label),
			"fieldtype": field.fieldtype,
			"reqd": bool(field.reqd),
			"options": select_options(meta, fieldname) if field.fieldtype == "Select" else [],
		}
	return {"fields": fields, "people": onboarding.firm_people() if is_approver() else []}


@frappe.whitelist(methods=["POST"])
def log_notice(
	title: str,
	case_type: str,
	forum: str,
	company: str,
	reply_by: str,
	notice_reference: str | None = None,
) -> dict:
	"""Record a notice that has just arrived, with its reply date, as the person who received it.

	The rest of the case is filled in later in the Desk; the app attaches a copy of the notice.
	"""
	check_app_access()
	frappe.has_permission("Legal Case", "create", throw=True)
	case = frappe.get_doc(
		{
			"doctype": "Legal Case",
			"title": title,
			"case_type": case_type,
			"forum": forum,
			"company": company,
			"notice_reference": notice_reference,
			"filing_date": nowdate(),
			"our_role": "Noticee",
			"status": "Open",
			"responsible": frappe.session.user,
		}
	).insert()
	frappe.get_doc(
		{
			"doctype": "Legal Date",
			"reference_doctype": "Legal Case",
			"reference_name": case.name,
			"kind": "Reply Due",
			"date": reply_by,
			"purpose": _("Reply to the notice"),
		}
	).insert()
	return {"name": case.name}


# What starting a case or trademark in the app may fill in; the rest is set later on its page.
NEW_CASE_FIELDS = (
	"title",
	"case_type",
	"forum",
	"forum_name",
	"case_number",
	"filing_date",
	"company",
	"our_role",
	"opposing_party",
	"appeal_of",
)
NEW_MARK_FIELDS = (
	"mark",
	"mark_type",
	"application_number",
	"filing_date",
	"applicant",
	"user_claim",
	"used_since",
)


def chosen_values(values: dict, allowed: tuple, doctype: str) -> dict:
	"""Only the fields a form may fill in, each a single value."""
	not_allowed = sorted(set(values) - set(allowed))
	if not_allowed:
		frappe.throw(
			_("A new {0} cannot set {1}.").format(_(doctype), ", ".join(not_allowed)), frappe.PermissionError
		)
	if any(not isinstance(value, PLAIN_VALUES) for value in values.values()):
		frappe.throw(_("Each field of a new {0} is a single value.").format(_(doctype)))
	return {field: value for field, value in values.items() if value not in (None, "")}


NEW_FILING_FIELDS = (
	"obligation_template",
	"company",
	"period_label",
	"period_end",
	"due_date",
	"responsible",
	"reviewer",
	"remarks",
)


@frappe.whitelist(methods=["GET"])
def billing_setup() -> dict:
	"""Whether the firm is set up to bill its clients, with its details for its bills."""
	check_app_access()
	billing.check_firm_manager()
	return billing.setup_state()


@frappe.whitelist(methods=["POST"])
def set_up_billing(details: dict, name: str | None = None) -> dict:
	"""Make the firm's own company for its bills (once, under `name`), and keep its GSTIN, state,
	address, bank details and bill prefix."""
	check_app_access()
	billing.check_firm_manager()
	if not billing_company_set() and not (name or "").strip():
		frappe.throw(_("Give the firm's name as it appears on its bills."))
	return billing.set_up_firm((name or "").strip(), details)


@frappe.whitelist(methods=["GET"])
def client_fees(client: str) -> dict:
	"""A client's fee plan, and its filed returns not billed yet with their fees."""
	check_app_access()
	billing.check_firm_manager()
	frappe.get_doc("Compliance Client", client).check_permission("read")
	return billing.client_fees(client)


@frappe.whitelist(methods=["GET"])
def bill_options(client: str, company: str | None = None) -> dict:
	"""What a new bill for one of a client's companies may hold."""
	check_app_access_or_accounts()
	check_billed_client(client)
	return billing.bill_options(client, company)


@frappe.whitelist(methods=["POST"])
def create_bill(
	client: str,
	filings: list | None = None,
	recurring: bool = False,
	lines: list | None = None,
	services: list | None = None,
	company: str | None = None,
) -> dict:
	"""A draft bill for one of a client's companies, from filings it has not been billed for, the
	recurring charges due this month, services done and other lines; checked and sent from its
	page."""
	check_app_access_or_accounts()
	billing.check_biller()
	check_billed_client(client)
	if not all(isinstance(name, str) for name in filings or []):
		frappe.throw(_("Filings are given by their names."))
	month = getdate(nowdate()).replace(day=1) if recurring else None
	return {
		"name": billing.make_bill(
			client, filings=filings, month=month, lines=lines, services=services, company=company
		)
	}


@frappe.whitelist(methods=["GET"])
def bill(name: str) -> dict:
	"""One of the firm's bills, for its page."""
	check_app_access_or_accounts()
	return billing.bill_detail(name)


@frappe.whitelist(methods=["POST"])
def send_bill(name: str) -> dict:
	"""Submit a draft bill and email it to the client."""
	check_app_access_or_accounts()
	return billing.send_bill(name)


@frappe.whitelist(methods=["POST"])
def cancel_bill(name: str) -> dict:
	"""Cancel a sent bill, or delete a draft."""
	check_app_access_or_accounts()
	billing.cancel_bill(name)
	return {"name": name}


@frappe.whitelist(methods=["POST"])
def record_payment(
	name: str,
	amount: float,
	paid_on: str,
	mode: str,
	reference: str | None = None,
	tds: float = 0,
	paid_by: str | None = None,
) -> dict:
	"""A payment received against a sent bill, in full or part, with any TDS the client deducted
	and, when noted, which of the client's companies paid."""
	check_app_access_or_accounts()
	return {"payment": billing.record_payment(name, amount, paid_on, mode, reference, tds, paid_by)}


@frappe.whitelist(methods=["POST"])
def credit_bill(name: str, reason: str, amount: float | None = None, line: str | None = None) -> dict:
	"""A credit note against a sent bill: every line left, or one line in full or in part."""
	check_app_access_or_accounts()
	return {"credit_note": billing.credit_note(name, reason, amount, line)}


@frappe.whitelist(methods=["POST"])
def write_off_bill(name: str, reason: str) -> dict:
	"""Write off what is still due on a sent bill."""
	check_app_access_or_accounts()
	return {"journal_entry": billing.write_off(name, reason)}


@frappe.whitelist(methods=["POST"])
def record_advance(
	client: str,
	amount: float,
	paid_on: str,
	mode: str,
	reference: str | None = None,
	paid_by: str | None = None,
) -> dict:
	"""Money a client pays before it is billed."""
	check_app_access_or_accounts()
	billing.check_biller()
	check_billed_client(client)
	return {"payment": billing.record_advance(client, amount, paid_on, mode, reference, paid_by)}


@frappe.whitelist(methods=["GET"])
def payments(
	client: str | None = None, text: str | None = None, start: int = 0, page_length: int = 20
) -> dict:
	"""One page of the payments the firm has received."""
	check_app_access_or_accounts()
	limit = min(max(1, cint(page_length)), MAX_PAGE_LENGTH)
	return billing.payments(client, text, max(0, cint(start)), limit)


@frappe.whitelist(methods=["GET"])
def payment(name: str) -> dict:
	"""A payment the firm received, as its page shows it."""
	check_app_access_or_accounts()
	return billing.payment_detail(name)


@frappe.whitelist(methods=["POST"])
def email_receipt(name: str) -> dict:
	"""Email a payment's receipt to the client."""
	check_app_access_or_accounts()
	return {"emailed_to": billing.email_receipt(name)}


@frappe.whitelist(methods=["POST"])
def cancel_payment(name: str) -> dict:
	"""Cancel a payment recorded against one of the firm's bills."""
	check_app_access_or_accounts()
	billing.cancel_payment(name)
	return {"name": name}


@frappe.whitelist(methods=["GET"])
def bill_pdf(name: str):
	"""A bill's PDF: for those who bill, and for the client it was sent to."""
	own = is_client_login()
	bill = own_bill(name) if own else billing_bill(name)
	# A client's login may not read ERPNext's invoices; own_bill has checked this one was sent to it,
	# so printing it is allowed for this one request only.
	frappe.flags.ignore_print_permissions = own
	try:
		pdf = frappe.get_print(
			"Sales Invoice",
			bill.name,
			doc=bill,
			print_format=billing.BILL_FORMAT,
			as_pdf=True,
			no_letterhead=1,
		)
	finally:
		frappe.flags.ignore_print_permissions = False
	frappe.local.response.filename = f"{bill.name.replace('/', '-')}.pdf"
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "pdf"


@frappe.whitelist(methods=["GET"])
def bills(
	view: str, client: str | None = None, text: str | None = None, start: int = 0, page_length: int = 20
) -> dict:
	"""One page of the firm's bills in a tab (drafts, unpaid, paid or all)."""
	check_app_access_or_accounts()
	limit = min(max(1, cint(page_length)), MAX_PAGE_LENGTH)
	return billing.bills(view, client, text, max(0, cint(start)), limit)


@frappe.whitelist(methods=["GET"])
def bill_counts(client: str | None = None, text: str | None = None) -> dict:
	"""How many bills each tab holds, and what is still due in it."""
	check_app_access_or_accounts()
	return billing.bill_counts(client, text)


@frappe.whitelist(methods=["GET"])
def client_billing(client: str) -> dict:
	"""A client's bills and balance: for those who bill, or for the client's own login."""
	return billing.client_billing(client, check_client_account(client))


def check_client_account(client: str) -> bool:
	"""A client's account is for those who bill, and for the client's own login; True for the latter."""
	check_reader_access()
	own = is_client_login()
	if own:
		if client != client_of_login():
			frappe.throw(_("You can see only your own bills."), frappe.PermissionError)
	else:
		billing.check_biller()
		check_billed_client(client)
	return own


@frappe.whitelist(methods=["GET"])
def client_summary(client: str) -> dict:
	"""Where a client stands with the firm this financial year, for those who bill."""
	if check_client_account(client):
		frappe.throw(_("Your firm's summary of your account is for the firm."), frappe.PermissionError)
	return billing.client_summary(client)


@frappe.whitelist(methods=["GET"])
def statement_pdf(client: str, from_date: str | None = None, to_date: str | None = None):
	"""A client's statement of account, this financial year unless dates are given: for those who
	bill, and for the client's own login."""
	from frappe.utils.pdf import get_chrome_pdf

	from kxcompliance.kx_compliance.client_reports import financial_year

	own = check_client_account(client)
	year_from, year_to = financial_year()
	html = billing.statement_html(client, from_date or year_from, to_date or year_to, own)
	frappe.local.response.filename = f"Statement-{client}.pdf".replace("/", "-")
	# Printed as bills are, through Chrome (their print formats' generator), not wkhtmltopdf.
	frappe.local.response.filecontent = get_chrome_pdf(None, html, {}, None, pdf_generator="chrome")
	frappe.local.response.type = "pdf"


def check_billed_client(client: str):
	"""The app's people bill only clients they may read; accounts staff bill any of the firm's."""
	if not frappe.db.exists("Compliance Client", client):
		frappe.throw(_("Client {0} does not exist.").format(client), frappe.DoesNotExistError)
	if has_app_access():
		frappe.get_doc("Compliance Client", client).check_permission("read")


@frappe.whitelist(methods=["GET"])
def receipt_pdf(name: str):
	"""A payment's receipt: for those who bill (an advance's too), and for the client who paid."""
	own = is_client_login()
	if own:
		entry = frappe.get_doc("Payment Entry", name) if frappe.db.exists("Payment Entry", name) else None
		bills = [
			row.reference_name
			for row in (entry.references if entry else [])
			if row.reference_doctype == "Sales Invoice"
		]
		if not bills:
			frappe.throw(
				_("{0} is not a payment against one of your bills.").format(name), frappe.PermissionError
			)
		own_bill(bills[0])
	else:
		check_app_access_or_accounts()
		entry = billing.payment_of(name)
	if entry.docstatus != 1:
		frappe.throw(_("{0} is cancelled; it has no receipt.").format(name))
	# As for a bill: a client's login may not read ERPNext's payments; its own bill was checked above.
	frappe.flags.ignore_print_permissions = own
	try:
		pdf = frappe.get_print(
			"Payment Entry",
			entry.name,
			doc=entry,
			print_format=billing.RECEIPT_FORMAT,
			as_pdf=True,
			no_letterhead=1,
		)
	finally:
		frappe.flags.ignore_print_permissions = False
	frappe.local.response.filename = f"{entry.name}.pdf"
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "pdf"


def billing_bill(name: str):
	check_app_access_or_accounts()
	return billing.bill_of(name)


def own_bill(name: str):
	"""A bill sent to the client whose login this is; its login reads it here, as it may not read
	ERPNext's invoices."""
	bill = frappe.get_doc("Sales Invoice", name) if frappe.db.exists("Sales Invoice", name) else None
	if (
		not bill
		or bill.docstatus != 1
		or not bill.compliance_client
		or bill.compliance_client != client_of_login()
	):
		frappe.throw(_("You can see only bills sent to you."), frappe.PermissionError)
	return bill


def check_app_access_or_accounts():
	"""The app's people, and accounts staff who bill the firm's clients."""
	if frappe.session.user == "Guest" or not (
		has_app_access() or billing.BILLING_ROLES & set(frappe.get_roles())
	):
		frappe.throw(_("You do not have access to the compliance app."), frappe.PermissionError)


def billing_company_set() -> bool:
	return bool(frappe.get_cached_doc("KX Compliance Settings").billing_company)


@frappe.whitelist(methods=["POST"])
def add_one_off_filing(filing: dict) -> dict:
	"""A filing outside the company's schedule: a return from the library, for a period or reason
	given here, by a due date. Held by whoever adds it; only a manager names someone else."""
	check_app_access()
	# Those who may work on filings may add one, as recording an event adds its filings; the
	# doctype's own create permission stays with managers and the schedule.
	frappe.has_permission("Compliance Task", "write", throw=True)
	values = chosen_values(filing, NEW_FILING_FIELDS, "Compliance Task")
	company, template = values.get("company"), values.get("obligation_template")
	if company not in app_companies():
		frappe.throw(_("You cannot add filings for {0}.").format(company), frappe.PermissionError)
	if not template or not frappe.db.get_value("Compliance Obligation Template", template, "is_active"):
		frappe.throw(
			_("Choose a return from the obligation library, not {0}.").format(template or _("nothing"))
		)
	for field, message in (("period_label", _("Say what it is for")), ("due_date", _("Give the due date"))):
		if not values.get(field):
			frappe.throw(_("{0} of the {1} filing.").format(message, template))
	user = frappe.session.user
	responsible = values.get("responsible") or user
	if (responsible != user or values.get("reviewer")) and not is_approver():
		frappe.throw(
			_("Only a Compliance Manager can choose who handles or reviews a filing."), frappe.PermissionError
		)
	companies.check_person(responsible, _("Responsible"))
	companies.check_person(values.get("reviewer"), _("Reviewer"))
	reviewer = values.get("reviewer") or frappe.db.get_value(
		"Company Compliance Profile", company, "default_reviewer"
	)
	doc = frappe.get_doc(
		{
			"doctype": "Compliance Task",
			**values,
			"responsible": responsible,
			# Nobody reviews what they prepare.
			"reviewer": reviewer if reviewer != responsible else None,
			"status": "Open",
			"task_key": f"one-off|{template}|{company}|{frappe.generate_hash(length=10)}",
		}
	)
	# Checked above: the person may work on filings and on this company, and chose only what
	# a filing's form offers (as company_events.make_task does for an event's filings).
	doc.flags.ignore_permissions = True
	doc.insert()
	return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def open_case(case: dict, next_hearing: str | None = None) -> dict:
	"""Start a case already under way (a suit, appeal or petition), held by whoever starts it, with
	its next hearing if there is one."""
	check_app_access()
	frappe.has_permission("Legal Case", "create", throw=True)
	doc = frappe.get_doc(
		{
			"doctype": "Legal Case",
			**chosen_values(case, NEW_CASE_FIELDS, "Legal Case"),
			"status": "Open",
			"responsible": frappe.session.user,
		}
	).insert()
	if next_hearing:
		frappe.get_doc(
			{
				"doctype": "Legal Date",
				"reference_doctype": "Legal Case",
				"reference_name": doc.name,
				"kind": "Hearing",
				"date": next_hearing,
			}
		).insert()
	return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def add_trademark(mark: dict, classes: list) -> dict:
	"""Record a trademark applied for or already held, held by whoever adds it."""
	check_app_access()
	frappe.has_permission("Trademark", "create", throw=True)
	rows = []
	for entry in classes:
		if (
			not isinstance(entry, dict)
			or set(entry) - {"class_number", "goods_or_services"}
			or not isinstance(entry.get("goods_or_services"), str | type(None))
		):
			frappe.throw(_("Each class is a number with what it covers."))
		rows.append(
			{
				"class_number": cint(entry.get("class_number")),
				"goods_or_services": entry.get("goods_or_services"),
			}
		)
	doc = frappe.get_doc(
		{
			"doctype": "Trademark",
			**chosen_values(mark, NEW_MARK_FIELDS, "Trademark"),
			"classes": rows,
			"responsible": frappe.session.user,
		}
	).insert()
	return {"name": doc.name}


def party_query(party_type: str, text: str) -> dict:
	"""Customers or suppliers whose ID or name contains `text`, not disabled."""
	check_party_type(party_type)
	text = (text or "").strip()
	name_field = PARTY_NAME_FIELDS[party_type]
	return {
		"filters": {"disabled": 0},
		"or_filters": {"name": ("like", f"%{text}%"), name_field: ("like", f"%{text}%")} if text else None,
	}


def read_parties(party_type: str, **query) -> list[dict]:
	if frappe.has_permission(party_type, "read"):
		return frappe.get_list(party_type, **query)
	# Compliance roles do not read Customer or Supplier; the check gives them names and groups only.
	return frappe.get_all(party_type, **query)


@frappe.whitelist(methods=["GET"])
def search_parties(
	party_type: str, text: str = "", start: int = 0, page_length: int = PARTY_SEARCH_LIMIT
) -> list[dict]:
	"""Customers or suppliers whose ID or name contains `text`, for the Licence Check, a page at a
	time (at most 100)."""
	name_field = PARTY_NAME_FIELDS.get(party_type)
	query = party_query(party_type, text)
	return read_parties(
		party_type,
		**query,
		fields=["name", f"{name_field} as party_name", f"{GROUP_FIELDS[party_type]} as party_group"],
		order_by=f"{name_field} asc",
		limit_start=max(0, cint(start)),
		limit=min(max(1, cint(page_length)), MAX_PAGE_LENGTH),
	)


@frappe.whitelist(methods=["GET"])
def count_parties(party_type: str, text: str = "") -> int:
	"""How many customers or suppliers the Licence Check search finds."""
	rows = read_parties(party_type, **party_query(party_type, text), fields=[{"COUNT": "*", "as": "count"}])
	return rows[0]["count"] if rows else 0


@frappe.whitelist(methods=["GET"])
def check_party(party_type: str, party: str) -> dict:
	"""Whether a customer or supplier holds the licences their sales or purchases need today."""
	check_party_type(party_type)
	if frappe.has_permission(party_type, "read"):
		frappe.has_permission(party_type, "read", doc=party, throw=True)
	details = frappe.db.get_value(
		party_type,
		party,
		[PARTY_NAME_FIELDS[party_type], GROUP_FIELDS[party_type]],
		as_dict=True,
	)
	if not details:
		frappe.throw(_("{0} {1} does not exist.").format(_(party_type), party), frappe.DoesNotExistError)

	today = getdate(nowdate())
	licences = party_licence_items(party_type, party)
	documents = [
		(doctype, check_field)
		for doctype, (side, check_field, _field, _date) in DOCUMENTS.items()
		if side == party_type
	]
	requirements = []
	for requirement in requirements_for_party(party_type, party):
		gap = licence_gap(requirement, licences, party_type, party, today) or {}
		requirements.append(
			{
				"item_type": requirement.item_type,
				"action": requirement.action,
				"grace_days": requirement.grace_days or 0,
				"item_groups": requirement.item_groups,
				"documents": [doctype for doctype, check_field in documents if requirement.get(check_field)],
				"result": gap.get("result", "ok"),
				"message": gap.get("message", ""),
			}
		)
	return {
		"party_type": party_type,
		"party": party,
		"party_name": details[PARTY_NAME_FIELDS[party_type]],
		"party_group": details[GROUP_FIELDS[party_type]],
		"checked_on": str(today),
		"requirements": requirements,
		"licences": [
			{
				"name": licence.name,
				"item_type": licence.item_type,
				"reference_number": licence.reference_number,
				"status": licence.status,
				"valid_until": licence.valid_until and str(licence.valid_until),
				"valid": is_valid_on(licence, today),
			}
			for licence in licences
		],
	}


@frappe.whitelist(methods=["GET"])
def full_names(users: str) -> dict[str, str]:
	"""People's names for the user IDs the app shows (responsible, reviewer), as the Desk shows them.

	`users` is comma-separated, since a GET request cannot carry a list; user IDs hold no commas.
	"""
	check_reader_access()
	wanted = sorted({user.strip() for user in users.split(",") if user.strip()})
	if len(wanted) > NAMES_LIMIT:
		frappe.throw(_("Ask for at most {0} names at a time.").format(NAMES_LIMIT))
	if not wanted:
		return {}
	# Names only, for people this app already shows by ID; Compliance roles do not read User.
	rows = frappe.get_all("User", filters={"name": ("in", wanted)}, fields=["name", "full_name"])
	return {row.name: row.full_name or row.name for row in rows}


def search_kinds(kind: str | None) -> list[str] | None:
	"""The kinds a search may look at: one asked for, or all (None); a client's login only those
	whose pages it opens. An empty list means nothing may be searched."""
	if kind is not None and not isinstance(kind, str):
		frappe.throw(_("Search one kind at a time."), frappe.ValidationError)
	kinds = [kind] if kind else None
	if is_client_login():
		# A client's login opens only these pages; the others' results would lead nowhere.
		kinds = [chosen for chosen in (kinds or CLIENT_SEARCH_KINDS) if chosen in CLIENT_SEARCH_KINDS]
	return kinds


def party_kinds(kind: str | None) -> dict[str, str]:
	"""The customer and supplier kinds a search covers, by key, for staff who may check them."""
	if is_client_login():
		return {}
	keys = {f"{party_type.lower()}s": party_type for party_type in party_types_to_check()}
	return {key: party_type for key, party_type in keys.items() if not kind or kind == key}


def searches_people(kind: str | None) -> bool:
	return (not kind or kind == "people") and is_approver() and has_app_access()


@frappe.whitelist(methods=["GET"])
def search(
	text: str, kind: str | None = None, start: int = 0, page_length: int | None = None
) -> dict[str, list]:
	"""Records with every word of `text` in their name, number or reference, closest first, as far
	as the person may read them: the register, filings, cases, trademarks, clients, companies,
	signatories, document requests, licence rules and obligations; for managers the team; and the
	customers and suppliers Licence Check may look at. `kind` asks for one of them only, and
	`start` and `page_length` (at most 100) for one page of it."""
	check_reader_access()
	kinds = search_kinds(kind)
	if kinds == []:
		return {}
	start = max(0, cint(start))
	limit = min(max(1, cint(page_length)), MAX_PAGE_LENGTH) if page_length else SEARCH_CANDIDATES
	found = search_records(text, kinds, start, limit)
	words = search_words(text)
	if len(" ".join(words)) < SEARCH_MIN_LENGTH:
		return found
	if searches_people(kind):
		found["people"] = search_people(words)[start : start + limit]
	for key, party_type in party_kinds(kind).items():
		found[key] = matching_parties(party_type, words).offset(start).limit(limit).run(as_dict=True)
	return found


@frappe.whitelist(methods=["GET"])
def search_counts(text: str) -> dict[str, int]:
	"""How many records of each kind a search finds, for the counts beside its tabs."""
	check_reader_access()
	kinds = search_kinds(None)
	if kinds == []:
		return {}
	counts = search_record_counts(text, kinds)
	words = search_words(text)
	if len(" ".join(words)) < SEARCH_MIN_LENGTH:
		return counts
	if searches_people(None):
		counts["people"] = len(search_people(words))
	for key, party_type in party_kinds(None).items():
		query = matching_parties(party_type, words, count=True)
		counts[key] = query.run(as_dict=True)[0]["count"]
	return counts


def search_people(words: list[str]) -> list[dict]:
	"""The team members with every word in their name or email (managers only, checked by the caller)."""
	return [
		person
		for person in people.team()
		if all(word in f"{person['full_name']} {person['user']}".lower() for word in words)
	]


def matching_parties(party_type: str, words: list[str], count: bool = False):
	"""The query for customers or suppliers with every word in their ID or name, for Licence
	Check, in name order; or, with `count`, how many there are."""
	name_field = PARTY_NAME_FIELDS[party_type]
	table = frappe.qb.DocType(party_type)
	if frappe.has_permission(party_type, "read"):
		# Someone who reads customers or suppliers sees only those their permissions allow.
		query = frappe.qb.get_query(
			party_type,
			fields=[{"COUNT": "*", "as": "count"}]
			if count
			else ["name", f"{name_field} as party_name", f"{GROUP_FIELDS[party_type]} as party_group"],
			ignore_permissions=False,
		)
	else:
		# Compliance roles do not read Customer or Supplier; Licence Check gives them names and
		# groups only, as search_parties does.
		query = frappe.qb.from_(table).select(
			*(
				[Count("*").as_("count")]
				if count
				else [
					table.name,
					table[name_field].as_("party_name"),
					table[GROUP_FIELDS[party_type]].as_("party_group"),
				]
			)
		)
	query = query.where(table.disabled == 0)
	for word in words:
		pattern = search_like(word)
		query = query.where((table.name.like(pattern)) | (table[name_field].like(pattern)))
	return query if count else query.orderby(table[name_field])


@frappe.whitelist(methods=["GET"])
def event_types(company: str) -> list[dict]:
	"""The events that call for a filing from this company, for recording one in the app."""
	check_app_access()
	if company not in app_companies():
		frappe.throw(_("You cannot record events for {0}.").format(company), frappe.PermissionError)
	company_type = frappe.db.get_value("Company Compliance Profile", company, "company_type")
	names = event_types_for(company_type) if company_type else []
	if not names:
		return []
	return frappe.get_all(
		"Compliance Event Type",
		filters={"name": ("in", names)},
		fields=["name", "description"],
		order_by="name asc",
	)


@frappe.whitelist(methods=["GET"])
def clients_overview() -> list[dict]:
	"""A CA/CS firm's clients the person may see, with their open filings, worst first."""
	check_app_access()
	return clients.clients_overview()


@frappe.whitelist(methods=["GET"])
def client_choices() -> list[dict]:
	"""The clients the person may pick to narrow the app's lists, each with its companies."""
	check_app_access()
	return clients.client_choices()


@frappe.whitelist(methods=["GET"])
def client_detail(client: str) -> dict:
	"""One client: its companies, team and open filings."""
	check_reader_access()
	return clients.client_detail(client)


@frappe.whitelist(methods=["GET"])
def onboarding_options() -> dict:
	"""What the onboarding screens offer: companies, kinds, registrations, states and people."""
	check_app_access()
	return onboarding.options()


@frappe.whitelist(methods=["POST"])
def complete_onboarding(setup: dict) -> dict:
	"""Set the site up from the onboarding answers. `setup` is read field by field, never stored whole."""
	check_app_access()
	return onboarding.complete(setup)


@frappe.whitelist(methods=["POST"])
def add_client_document(task: str) -> dict:
	"""A client's login attaches a document (the file in the request) to one of its filings.

	The client may read the filing but not change it, so this is the one thing it may add; the
	filing's responsible person is told.
	"""
	if not is_client_login():
		frappe.throw(_("Only a client's login adds documents this way."), frappe.PermissionError)
	filing = frappe.get_doc("Compliance Task", task)
	filing.check_permission("read")
	document = attach_upload("Compliance Task", filing.name)
	if filing.responsible:
		enqueue_create_notification(
			filing.responsible,
			{
				"type": "Alert",
				"document_type": "Compliance Task",
				"document_name": filing.name,
				"from_user": frappe.session.user,
				"subject": _("{0} uploaded {1} for {2} ({3})").format(
					frappe.utils.get_fullname(frappe.session.user),
					document.file_name,
					filing.obligation_template,
					filing.period_label or filing.name,
				),
			},
		)
	return {"name": document.name, "file_name": document.file_name, "file_url": document.file_url}


@frappe.whitelist(methods=["POST"])
def add_request_document(request: str) -> dict:
	"""The client (or the firm, for a document it received another way) uploads what a Document
	Request asks for (the file in the request)."""
	check_reader_access()
	doc = frappe.get_doc("Document Request", request)
	doc.check_permission("read")
	if not (is_client_login() or doc.has_permission("write")):
		frappe.throw(_("You cannot upload to {0}.").format(doc.name), frappe.PermissionError)
	if doc.status not in document_requests.OPEN_STATUSES:
		frappe.throw(_("{0} is {1}; nothing more can be uploaded to it.").format(doc.name, _(doc.status)))
	document = attach_upload("Document Request", doc.name)
	document_requests.received(doc, document)
	return {"name": document.name, "file_name": document.file_name, "file_url": document.file_url}


def attach_upload(doctype: str, name: str):
	"""Attach the file in this request to a record the caller may read (checked by the caller)."""
	upload = frappe.request.files.get("file") if frappe.request else None
	if not upload or not upload.filename:
		frappe.throw(_("Choose a file to upload."))
	if guess_type(upload.filename)[0] not in ALLOWED_MIMETYPES:
		frappe.throw(_("You can only upload JPG, PNG, GIF, PDF, TXT, CSV or Microsoft documents."))
	document = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": upload.filename,
			"attached_to_doctype": doctype,
			"attached_to_name": name,
			"is_private": 1,
			"content": upload.stream.read(),
		}
	)
	# Attaching needs write on the record, which a client does not have; read was checked first.
	document.insert(ignore_permissions=True)
	return document


DOCUMENT_DOCTYPES = ("Compliance Task", "Compliance Item", "Legal Case", "Trademark", "Document Request")
DOCUMENTS_LIMIT = 50


@frappe.whitelist(methods=["GET"])
def documents(doctype: str, name: str) -> list[dict]:
	"""The files attached to a record the person may read, newest first."""
	check_reader_access()
	if doctype not in DOCUMENT_DOCTYPES:
		frappe.throw(_("Documents are not shown for {0}.").format(doctype), frappe.PermissionError)
	frappe.get_doc(doctype, name).check_permission("read")
	# A client's login may list only files it uploaded itself; reading the record is what counts.
	return frappe.get_all(
		"File",
		filters={"attached_to_doctype": doctype, "attached_to_name": name},
		fields=["name", "file_name", "file_url", "owner", "creation"],
		order_by="creation desc",
		limit=DOCUMENTS_LIMIT,
	)


def client_of_login() -> str:
	"""The client a client's login belongs to; the first one if a person is at several."""
	if not is_client_login():
		return ""
	clients = frappe.get_list("Compliance Client", filters={"status": ("!=", "Left")}, pluck="name", limit=1)
	return clients[0] if clients else ""


@frappe.whitelist(methods=["GET"])
def filing_penalty(task: str) -> dict:
	"""What filing late costs, or would cost, for one filing the person may read."""
	check_reader_access()
	doc = frappe.get_doc("Compliance Task", task)
	doc.check_permission("read")
	return score.filing_penalty(doc)


@frappe.whitelist(methods=["GET"])
def companies_overview() -> dict:
	"""Companies set up for compliance, and those not yet (managers only)."""
	check_app_access()
	return companies.companies_overview()


@frappe.whitelist(methods=["GET"])
def company_form_options() -> dict:
	"""What the company screen offers to choose from (managers only)."""
	check_app_access()
	return companies.form_options()


@frappe.whitelist(methods=["GET"])
def company_detail(company: str) -> dict:
	"""A company's compliance profile, for its screen (managers only)."""
	check_app_access()
	return companies.company_detail(company)


@frappe.whitelist(methods=["POST"])
def save_company(company: str, values: dict, new_company: bool = False) -> dict:
	"""Set a company up or change its profile; `values` is read field by field (managers only)."""
	check_app_access()
	return companies.save_company(company, values, new_company)


@frappe.whitelist(methods=["GET"])
def people_options() -> list[dict]:
	"""The firm's people who can be given compliance work, for the app's forms (names only)."""
	check_app_access()
	return onboarding.firm_people()


@frappe.whitelist(methods=["GET"])
def item_form_options() -> dict:
	"""What the register item screen offers to choose from."""
	check_app_access()
	meta = frappe.get_meta("Compliance Item")
	return {
		"item_types": frappe.get_list(
			"Compliance Item Type",
			filters={"is_active": 1},
			fields=["name", "category", "renewal_cycle_months", "requires_document"],
			order_by="name asc",
		),
		"states": [state for state in meta.get_field("state").options.split("\n") if state],
		"billing_cycles": [cycle for cycle in meta.get_field("billing_cycle").options.split("\n") if cycle],
		"people": onboarding.firm_people(),
	}


@frappe.whitelist(methods=["GET"])
def tours_seen() -> dict:
	"""The tours this person has already been shown (staff and client logins)."""
	check_reader_access()
	return tours.seen()


@frappe.whitelist(methods=["POST"])
def tour_opened(tour: str) -> dict:
	"""This person started a tour; counted every time, and the first time marks it seen."""
	check_reader_access()
	return tours.opened(tour)


def check_can_open_app():
	"""For what everyone who signs in to the app may do about their own data."""
	if frappe.session.user == "Guest" or not can_open_app():
		frappe.throw(_("You do not have access to the compliance app."), frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def privacy_notice() -> dict:
	"""The privacy notice, and whether this person has accepted its current version."""
	check_can_open_app()
	return privacy.notice()


@frappe.whitelist(methods=["POST"])
def accept_privacy_notice(version: int) -> dict:
	"""This person accepts the version of the privacy notice they were shown."""
	check_can_open_app()
	return privacy.accept(version)


@frappe.whitelist(methods=["POST"])
def withdraw_privacy_consent() -> dict:
	"""This person withdraws their consent; the app asks for it again before they use it."""
	check_can_open_app()
	return privacy.withdraw()


@frappe.whitelist(methods=["POST"])
def raise_privacy_request(request_type: str, details: str) -> dict:
	"""Ask to see, correct or erase one's own data, or raise a grievance."""
	check_can_open_app()
	return privacy.raise_request(request_type, details)


@frappe.whitelist(methods=["GET"])
def my_privacy_requests() -> list[dict]:
	"""This person's own privacy requests and the answers."""
	check_can_open_app()
	return privacy.my_requests()


# The languages the app is translated into (frontend/src/locales).
APP_LANGUAGES = ("en", "hi")


@frappe.whitelist(methods=["POST"])
def set_my_language(language: str) -> dict:
	"""Read the app in English or Hindi: the person's own Frappe language."""
	check_can_open_app()
	if language not in APP_LANGUAGES:
		frappe.throw(_("The app is not available in {0}.").format(language))
	user = frappe.get_doc("User", frappe.session.user)
	user.language = language
	# A person changes only their own language here; the User form would let them do the same.
	user.save(ignore_permissions=True)
	return {"language": language}


@frappe.whitelist(methods=["GET"])
def team() -> list[dict]:
	"""Everyone on the team and their role, for the People screen (managers only)."""
	check_app_access()
	return people.team()


@frappe.whitelist(methods=["POST"])
def invite_person(full_name: str, email: str, role: str) -> dict:
	"""Add someone to the team as Manager, Staff or Auditor (managers only)."""
	check_app_access()
	return people.invite(full_name, email, role)


@frappe.whitelist(methods=["POST"])
def set_person_role(user: str, role: str) -> dict:
	check_app_access()
	return people.set_role(user, role)


@frappe.whitelist(methods=["POST"])
def remove_person(user: str) -> dict:
	"""Take someone off the team; their work stays as it is."""
	check_app_access()
	return people.remove(user)


@frappe.whitelist(methods=["GET"])
def person(user: str) -> dict:
	"""One person on the team, with the open work they hold, for their page (managers only)."""
	check_app_access()
	return people.person(user)


@frappe.whitelist(methods=["POST"])
def send_password_reset(user: str) -> dict:
	"""Email someone the link to set a new password themselves (managers only)."""
	check_app_access()
	return people.send_password_reset(user)


@frappe.whitelist(methods=["POST"])
def set_temporary_password(user: str, password: str) -> dict:
	"""Set a password for someone to pass on in person, ending their open sessions (managers only)."""
	check_app_access()
	return people.set_temporary_password(user, password)


@frappe.whitelist(methods=["POST"])
def hand_over_work(from_user: str, to_user: str) -> dict:
	"""Move someone's open work and their places on companies and clients to another person on
	the team; it runs in the background and the manager is told when it is done (managers only)."""
	check_app_access()
	return people.start_handover(from_user, to_user)


@frappe.whitelist(methods=["GET"])
def former_people() -> list[dict]:
	"""People taken off the team who still hold open work, to hand it over (managers only)."""
	check_app_access()
	return people.former_holders()


@frappe.whitelist(methods=["POST"])
def new_sign_in_link(user: str) -> dict:
	"""A fresh link to set a password, for someone added who has never signed in."""
	check_app_access()
	return people.new_sign_in_link(user)


@frappe.whitelist(methods=["GET"])
def getting_started_checklist() -> dict:
	"""The first-week checklist for a manager's My Work, each step ticked when done."""
	check_app_access()
	return getting_started.checklist()


@frappe.whitelist(methods=["POST"])
def hide_getting_started():
	check_app_access()
	getting_started.hide()


@frappe.whitelist(methods=["GET"])
def month_events(start: str, end: str, companies: str | None = None) -> list[dict]:
	"""What falls on each day from `start` to `end` that the person may see, for the app's calendar.

	`companies`, a JSON list of company names, narrows it to a client's companies (the client
	filter); none means all. A GET request carries it as text, so it is read and checked here.
	"""
	check_app_access()
	return month_calendar.month_events(start, end, company_list(companies))


@frappe.whitelist(methods=["GET"])
def bulk_filing_choices(companies: str | None = None) -> list[dict]:
	"""The returns and periods the person has open filings for, soonest due first, for filing in bulk;
	`companies` (the client filter, as for the overview) keeps to one client's."""
	check_app_access()
	filters = {"status": ("in", BULK_STATUSES)}
	chosen = company_list(companies)
	if chosen is not None:
		filters["company"] = ("in", chosen or [""])
	rows = frappe.get_list(
		"Compliance Task",
		filters=filters,
		fields=[
			"obligation_template",
			"period_end",
			"period_label",
			{"MIN": "effective_due_date", "as": "due"},
			{"COUNT": "*", "as": "filings"},
		],
		group_by="obligation_template, period_end, period_label",
		order_by="due asc",
		limit=BULK_CHOICES_LIMIT,
	)
	return [
		{
			"obligation_template": row.obligation_template,
			"period_end": str(row.period_end),
			"period_label": row.period_label,
			"due": str(row.due),
			"filings": row.filings,
		}
		for row in rows
	]


def bulk_filings_of(obligation_template: str, period_end: str, companies: str | None) -> list[dict]:
	"""The open filings of one return and period the person may read, of one client's or all."""
	filters = {
		"obligation_template": obligation_template,
		"period_end": period_end,
		"status": ("in", BULK_STATUSES),
	}
	chosen = company_list(companies)
	if chosen is not None:
		filters["company"] = ("in", chosen or [""])
	return frappe.get_list(
		"Compliance Task", filters=filters, fields=["name", "company", "effective_due_date"], limit=1000
	)


@frappe.whitelist(methods=["GET"])
def bulk_ask_plan(obligation_template: str, period_end: str, companies: str | None = None) -> dict:
	"""How many clients asking for a document on a return and period would reach, and why not the rest."""
	check_app_access()
	plan = document_requests.bulk_plan(bulk_filings_of(obligation_template, period_end, companies))
	return {
		"to_ask": len(plan["to_ask"]),
		"asked_already": plan["asked_already"],
		"no_client": plan["no_client"],
	}


@frappe.whitelist(methods=["POST"])
def ask_clients_in_bulk(
	obligation_template: str,
	period_end: str,
	title: str,
	details: str | None = None,
	companies: str | None = None,
) -> dict:
	"""Ask every client with an open filing of this return and period for the same document; one
	request per filing, made in the background, and the person is told when it is done."""
	check_app_access()
	frappe.has_permission("Document Request", "create", throw=True)
	if not (title or "").strip():
		frappe.throw(_("Say what you are asking for."))
	plan = document_requests.bulk_plan(bulk_filings_of(obligation_template, period_end, companies))
	if not plan["to_ask"]:
		frappe.throw(
			_("Every client with this return already has a request open, or none is linked to a client.")
		)
	frappe.enqueue(
		"kxcompliance.kx_compliance.document_requests.run_ask_in_bulk",
		queue="long",
		enqueue_after_commit=True,
		filings=[dict(row) for row in plan["to_ask"]],
		title=title.strip(),
		details=(details or "").strip() or None,
		by=frappe.session.user,
	)
	return {"asking": len(plan["to_ask"])}


@frappe.whitelist(methods=["GET"])
def licence_rule_options() -> dict:
	"""What the licence rule screen offers: licence types, item and party groups, and the selling
	and buying documents a rule can be checked on (managers only)."""
	check_manager_access(_("Only a Compliance Manager can change licence rules."))
	documents = [
		{"doctype": doctype, "party_type": party_type, "field": check_field}
		for doctype, (party_type, check_field, _field, _date) in DOCUMENTS.items()
	]
	# Group names only, to choose from: a Compliance Manager is not given ERPNext's selling and
	# buying masters, and the rule they save is governed by Licence Requirement's own permissions.
	groups = {
		key: frappe.get_all(doctype, pluck="name", order_by="name asc", limit=500)
		for key, doctype in (
			("item_groups", "Item Group"),
			("customer_groups", "Customer Group"),
			("supplier_groups", "Supplier Group"),
		)
	}
	return {
		"item_types": frappe.get_list(
			"Compliance Item Type", filters={"is_active": 1}, pluck="name", order_by="name asc"
		),
		**groups,
		"documents": documents,
	}


@frappe.whitelist(methods=["GET"])
def obligation_form_options() -> dict:
	"""What the obligation screen offers to choose from (managers only)."""
	check_manager_access(_("Only a Compliance Manager can change the obligation library."))
	meta = frappe.get_meta("Compliance Obligation Template")
	return {
		**{field: select_options(meta, field) for field in OBLIGATION_CHOICES},
		"company_types": select_options(frappe.get_meta("Compliance Company Type"), "company_type"),
		"states": select_options(frappe.get_meta("Company Obligation"), "state"),
		"event_types": frappe.get_list("Compliance Event Type", pluck="name", order_by="name asc"),
	}


@frappe.whitelist(methods=["GET"])
def extension_preview(obligation_template: str, periods_ending_from: str, periods_ending_to: str) -> dict:
	"""How many open filings an extension with these periods would move (managers only)."""
	check_manager_access(_("Only a Compliance Manager can extend due dates."))
	rows = frappe.get_list(
		"Compliance Task",
		filters={
			"obligation_template": obligation_template,
			"period_end": ("between", [getdate(periods_ending_from), getdate(periods_ending_to)]),
			"status": ("not in", CLOSED_TASK_STATUSES),
		},
		fields=["company"],
	)
	return {"filings": len(rows), "companies": len({row.company for row in rows})}


@frappe.whitelist(methods=["GET"])
def settings_options() -> dict:
	"""The app's settings screen: the values and the choices it offers (managers only)."""
	check_app_access()
	return app_settings.options()


@frappe.whitelist(methods=["POST"])
def save_settings(values: dict) -> dict:
	"""Change the app's settings; only the fields the settings screen shows."""
	check_app_access()
	return app_settings.save(values)


@frappe.whitelist(methods=["GET"])
def setup_template():
	"""The bulk setup sheet to fill in, as an Excel file."""
	check_app_access()
	if not is_approver():
		frappe.throw(_("Only a Compliance Manager can set up companies in bulk."), frappe.PermissionError)
	frappe.response.filename = "kxcompliance-bulk-setup.xlsx"
	frappe.response.filecontent = setup_import.template()
	frappe.response.type = "binary"


def app_companies() -> list[str]:
	"""The companies the person may pick in the app: their User Permissions, else every company.

	Compliance roles do not read Company itself, so the app is given just the names.
	"""
	allowed = frappe.permissions.get_user_permissions(frappe.session.user).get("Company")
	if allowed:
		return sorted({permission.get("doc") for permission in allowed})
	if is_client_login():
		return []  # a client whose companies are not linked yet sees none, never every company
	return compliance_companies()


def boot() -> dict:
	settings = frappe.get_cached_doc("KX Compliance Settings")
	companies = app_companies() if has_app_access() or is_client_login() else []
	default = frappe.defaults.get_user_default("Company") or ""
	return {
		"user": frappe.session.user,
		"user_fullname": frappe.utils.get_fullname(frappe.session.user),
		"roles": sorted((APP_ROLES | set(CHECK_ROLES) | {CLIENT_ROLE}) & set(frappe.get_roles())),
		"party_types": party_types_to_check(),
		"app_name": settings.app_name or "KlyONIX Compliance",
		"app_logo": settings.app_logo or "",
		"csrf_token": frappe.sessions.get_csrf_token(),
		"site_name": frappe.local.site,
		"companies": companies,
		"client": client_of_login(),
		# Never the firm's own billing company, which is not a compliance company.
		"default_company": default if default in companies else "",
		"date_format": frappe.db.get_default("date_format") or "dd-mm-yyyy",
		"account_type": settings.account_type or "",
		# Billing clients: a firm set up to bill, and someone ERPNext lets make invoices.
		"may_bill": settings.account_type == "CA/CS Firm"
		and bool(settings.billing_company)
		and bool(frappe.has_permission("Sales Invoice", "create")),
		"lang": frappe.local.lang or "en",
		# A firm checks its clients' sales and purchases only for the clients it switches on.
		"licence_check_on": settings.account_type != "CA/CS Firm"
		or bool(frappe.db.exists("Compliance Client", {"licence_check": 1})),
		# Managers are taken through onboarding until the site is set up.
		"setup_needed": not settings.setup_complete and is_approver(),
		# Where the browser reaches Frappe's realtime server in development; behind a proxy in
		# production it is the site's own address.
		"socketio_port": frappe.conf.socketio_port or 9000,
		# Everyone reads and accepts the privacy notice before using the app.
		"privacy_notice_due": can_open_app() and privacy.notice_due(),
	}
