# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Whitelisted methods for the KlyONIX Compliance app at /compliance."""

from mimetypes import guess_type

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
from frappe.handler import ALLOWED_MIMETYPES
from frappe.utils import add_days, get_datetime, getdate, now_datetime, nowdate

from kxcompliance.install import CLIENT_ROLE
from kxcompliance.kx_compliance import (
	app_settings,
	clients,
	companies,
	document_requests,
	getting_started,
	month_calendar,
	onboarding,
	people,
	score,
	setup_import,
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
from kxcompliance.kx_compliance.register import CLOSED_TASK_STATUSES, is_approver

APP_ROLES = frozenset({"System Manager", "Compliance Manager", "Compliance User", "Compliance Auditor"})
# People who sell or buy may open the app for the Licence Check only, for their side of the business.
CHECK_ROLES = {"Sales User": "Customer", "Purchase User": "Supplier"}
PARTY_NAME_FIELDS = {"Customer": "customer_name", "Supplier": "supplier_name"}
PARTY_SEARCH_LIMIT = 20
NAMES_LIMIT = 50
SEARCH_LIMIT = 6
SEARCH_MIN_LENGTH = 2
# What the app's search looks through: the fields matched and the fields shown, per record type.
SEARCHES = {
	"items": (
		"Compliance Item",
		["title", "reference_number"],
		["name", "title", "item_type", "status", "valid_until", "reference_number"],
	),
	"filings": (
		"Compliance Task",
		["obligation_template", "acknowledgement_number", "period_label"],
		[
			"name",
			"obligation_template",
			"period_label",
			"company",
			"status",
			"is_overdue",
			"effective_due_date",
			"filed_on",
		],
	),
	"cases": (
		"Legal Case",
		["title", "case_number", "notice_reference", "cnr_number"],
		["name", "title", "case_type", "forum", "forum_name", "case_number", "status", "next_date"],
	),
	"trademarks": (
		"Trademark",
		["mark", "application_number", "registration_number"],
		["name", "mark", "application_number", "status", "next_date"],
	),
}
WORK_HORIZON_DAYS = 30
WORK_LIMIT = 200
# Filings that can still be filed or reviewed in bulk, and how many return-and-period choices to offer.
BULK_STATUSES = ("Open", "In Progress", "Ready for Review")
BULK_CHOICES_LIMIT = 100
# The obligation screen's choices, read from the template's own select fields.
OBLIGATION_CHOICES = ("law", "frequency", "period_basis", "registration_type")

# The only fields the app may change on each record; everything else stays in the Desk.
EDITABLE_FIELDS = {
	"Compliance Item": ("certificate", "reference_number", "notes"),
	"Compliance Task": (
		"status",
		"filed_on",
		"acknowledgement_number",
		"proof",
		"amount_paid",
		"interest",
		"late_fee",
		"remarks",
	),
	"Legal Date": ("status", "attended_by", "proceedings", "order", "next_date"),
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
def my_work() -> dict:
	"""What the signed-in person holds or reviews and should look at now, soonest first."""
	check_app_access()
	user = frappe.session.user
	mine = {"responsible": user, "reviewer": user}
	horizon = add_days(nowdate(), WORK_HORIZON_DAYS)
	return {
		"items": frappe.get_list(
			"Compliance Item",
			filters={
				"status": ("in", ["Draft", "Due for Renewal", "Expired", "Lapsed", "Renewal in Progress"])
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
			filters={"status": ("not in", CLOSED_TASK_STATUSES), "effective_due_date": ("<=", horizon)},
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
			filters={"status": "Scheduled", "date": ("<=", horizon)},
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
		"as_of": str(now_datetime()),
	}


@frappe.whitelist(methods=["GET"])
def overview() -> dict:
	"""The managers' numbers across the register, filings, legal work and party licences."""
	check_app_access()
	if not is_approver():
		frappe.throw(_("Only a Compliance Manager can open the overview."), frappe.PermissionError)
	return get_overview()


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
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")
	if base_modified and get_datetime(doc.modified) != get_datetime(base_modified):
		frappe.throw(
			_("{0} {1} was changed by someone else after this change was made.").format(_(doctype), name),
			frappe.TimestampMismatchError,
		)
	doc.update(values)
	doc.save()
	return {"name": doc.name, "modified": str(doc.modified)}


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


@frappe.whitelist(methods=["GET"])
def search_parties(party_type: str, text: str = "") -> list[dict]:
	"""Customers or suppliers whose ID or name contains `text`, for the Licence Check."""
	check_party_type(party_type)
	name_field = PARTY_NAME_FIELDS[party_type]
	query = {
		"filters": {"disabled": 0},
		"or_filters": {"name": ("like", f"%{text.strip()}%"), name_field: ("like", f"%{text.strip()}%")}
		if text.strip()
		else None,
		"fields": ["name", f"{name_field} as party_name", f"{GROUP_FIELDS[party_type]} as party_group"],
		"order_by": f"{name_field} asc",
		"limit": PARTY_SEARCH_LIMIT,
	}
	if frappe.has_permission(party_type, "read"):
		return frappe.get_list(party_type, **query)
	# Compliance roles do not read Customer or Supplier; the check gives them names and groups only.
	return frappe.get_all(party_type, **query)


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


@frappe.whitelist(methods=["GET"])
def search(text: str) -> dict[str, list]:
	"""Register items, filings, cases and trademarks whose name, number or reference contains
	`text`, a few of each, as far as the person may read them."""
	check_reader_access()
	text = text.strip()
	if len(text) < SEARCH_MIN_LENGTH:
		return {section: [] for section in SEARCHES}
	pattern = f"%{text}%"
	return {
		section: frappe.get_list(
			doctype,
			or_filters={field: ("like", pattern) for field in matched},
			fields=shown,
			order_by="modified desc",
			limit=SEARCH_LIMIT,
		)
		for section, (doctype, matched, shown) in SEARCHES.items()
	}


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
	chosen = frappe.parse_json(companies) if companies else None
	if chosen is not None and not (
		isinstance(chosen, list) and all(isinstance(name, str) for name in chosen)
	):
		frappe.throw(_("Companies must be a list of company names."), frappe.ValidationError)
	return month_calendar.month_events(start, end, chosen)


@frappe.whitelist(methods=["GET"])
def bulk_filing_choices() -> list[dict]:
	"""The returns and periods the person has open filings for, soonest due first, for filing in bulk."""
	check_app_access()
	rows = frappe.get_list(
		"Compliance Task",
		filters={"status": ("in", BULK_STATUSES)},
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
	return frappe.get_all("Company", pluck="name", order_by="name")


def boot() -> dict:
	settings = frappe.get_cached_doc("KX Compliance Settings")
	return {
		"user": frappe.session.user,
		"user_fullname": frappe.utils.get_fullname(frappe.session.user),
		"roles": sorted((APP_ROLES | set(CHECK_ROLES) | {CLIENT_ROLE}) & set(frappe.get_roles())),
		"party_types": party_types_to_check(),
		"app_name": settings.app_name or "KlyONIX Compliance",
		"app_logo": settings.app_logo or "",
		"csrf_token": frappe.sessions.get_csrf_token(),
		"site_name": frappe.local.site,
		"companies": app_companies() if has_app_access() or is_client_login() else [],
		"client": client_of_login(),
		"default_company": frappe.defaults.get_user_default("Company") or "",
		"date_format": frappe.db.get_default("date_format") or "dd-mm-yyyy",
		"account_type": settings.account_type or "",
		# Managers are taken through onboarding until the site is set up.
		"setup_needed": not settings.setup_complete and is_approver(),
	}
