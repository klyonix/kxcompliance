# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""First-run onboarding in the app: who the site is for, the first company (an existing
ERPNext company or a new one), its kind, registrations and people. Completing it makes the
compliance profile, finds the company's obligations in the library and makes the first tasks."""

import re
from datetime import date

import frappe
from frappe import _
from frappe.utils import formatdate, getdate, nowdate

from kxcompliance import scoped
from kxcompliance.kx_compliance.register import APPROVER_ROLES, client_named, compliance_companies
from kxcompliance.kx_compliance.statutory import generate_tasks

SETTINGS = "KX Compliance Settings"
ACCOUNT_TYPES = ("Organisation", "CA/CS Firm")
# Registrations whose state decides which filings apply (QRMP dates, state taxes).
STATE_REGISTRATIONS = {"GST", "GST Composition", "PT", "LWF"}
PEOPLE_ROLES = ("Compliance Manager", "Compliance User", "System Manager")


def select_options(doctype: str, fieldname: str) -> list[str]:
	return [
		option
		for option in (frappe.get_meta(doctype).get_field(fieldname).options or "").split("\n")
		if option
	]


def check_can_onboard():
	if not set(APPROVER_ROLES) & set(frappe.get_roles()):
		frappe.throw(_("Only a Compliance Manager can set up the app."), frappe.PermissionError)


def firm_people() -> list[dict]:
	"""Active users who can hold or review compliance work, by name, for choosing in a form.
	Names and IDs only: compliance roles do not otherwise read User."""
	users = sorted(
		set(
			scoped.get_all(
				"Has Role", filters={"role": ("in", PEOPLE_ROLES), "parenttype": "User"}, pluck="parent"
			)
		)
		- {"Guest"}
	)
	return scoped.get_all(
		"User",
		filters={"name": ("in", users or [""]), "enabled": 1, "user_type": "System User"},
		fields=["name", "full_name"],
		order_by="full_name asc",
	)


def options() -> dict:
	"""What the onboarding screens offer to choose from."""
	check_can_onboard()
	with_profile = set(scoped.get_all("Company Compliance Profile", pluck="company"))
	people = firm_people()
	return {
		"companies": [{"name": name, "set_up": name in with_profile} for name in compliance_companies()],
		"company_types": select_options("Company Compliance Profile", "company_type"),
		"registration_types": select_options("Compliance Registration", "registration_type"),
		"state_registrations": sorted(STATE_REGISTRATIONS),
		"states": select_options("Compliance Registration", "state"),
		"people": people,
		"agm_company_types": agm_company_types(),
		"last_year_end": last_year_end(getdate(nowdate())),
		"can_create_company": bool(frappe.has_permission("Company", "create")),
		# ERPNext's own setup (currency, fiscal year, basic records) must be done before a
		# company can be created; running it from here is not done yet (RK, 15 Nov 2026).
		"system_ready": bool(frappe.is_setup_complete()),
	}


def agm_company_types() -> list[str]:
	"""Kinds of company with filings that fall due after the AGM (AOC-4, MGT-7, ADT-1)."""
	templates = scoped.get_all(
		"Compliance Obligation Template",
		filters={"due_after_event": 1, "event_type": ("is", "not set"), "is_active": 1},
		pluck="name",
	)
	if not templates:
		return []
	kinds = select_options("Company Compliance Profile", "company_type")
	return [
		kind
		for kind in kinds
		if any(
			frappe.get_cached_doc("Compliance Obligation Template", name).applies_to(kind)
			for name in templates
		)
	]


def last_year_end(today: date) -> date:
	"""The end of the last financial year that has ended: 31 March this year or last."""
	return date(today.year if today.month > 3 else today.year - 1, 3, 31)


def clean_agm_date(value: str | None, today: date) -> list[dict]:
	"""Last year's AGM as the profile's AGM row, if it was given; it was held after the year ended
	and is not in the future."""
	if not value:
		return []
	if not isinstance(value, str):
		frappe.throw(_("Give the AGM date as a single date."))
	held, year_end = getdate(value), last_year_end(today)
	if not year_end < held <= today:
		frappe.throw(
			_("The AGM for the year ended {0} is held after that and by today, not on {1}.").format(
				formatdate(year_end), formatdate(held)
			)
		)
	return [{"financial_year_end": year_end, "agm_date": held}]


def company_abbr(name: str) -> str:
	"""Initials for a new company's abbreviation, numbered if another company has them."""
	initials = "".join(word[0] for word in re.findall(r"[A-Za-z0-9]+", name)).upper()[:5] or "CO"
	abbr, number = initials, 1
	while scoped.exists("Company", {"abbr": abbr}):
		number += 1
		abbr = f"{initials}{number}"
	return abbr


def make_company(name: str) -> str:
	# A new ERPNext company is made with the person's own rights: a Compliance Manager without
	# rights to create companies chooses an existing one instead.
	if not frappe.is_setup_complete():
		frappe.throw(_("Finish the system setup in the Desk first; it prepares what a new company needs."))
	if not frappe.has_permission("Company", "create"):
		frappe.throw(
			_("You cannot create companies; choose an existing one, or ask a System Manager."),
			frappe.PermissionError,
		)
	name = name.strip()
	if scoped.exists("Company", name):
		frappe.throw(_("A company named {0} already exists; choose it instead.").format(name))
	scoped.check_limit("Company", company_name=name)
	company = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": name,
			"abbr": company_abbr(name),
			"country": frappe.db.get_default("country") or "India",
			"default_currency": frappe.db.get_default("currency") or "INR",
		}
	)
	company.insert()
	return company.name


def clean_registrations(rows: list) -> list[dict]:
	"""Only the registration fields the profile takes, checked one row at a time."""
	allowed = set(select_options("Compliance Registration", "registration_type"))
	states = set(select_options("Compliance Registration", "state"))
	cleaned = []
	for index, row in enumerate(rows or [], start=1):
		kind = (row.get("registration_type") or "").strip()
		number = (row.get("registration_number") or "").strip()
		state = (row.get("state") or "").strip()
		if kind not in allowed:
			frappe.throw(_("Registration {0}: {1} is not a registration the app knows.").format(index, kind))
		if not number:
			frappe.throw(_("Registration {0}: enter the {1} number.").format(index, kind))
		if kind in STATE_REGISTRATIONS and state not in states:
			frappe.throw(_("Registration {0}: choose the state of the {1} registration.").format(index, kind))
		cleaned.append({"registration_type": kind, "registration_number": number, "state": state or None})
	return cleaned


def set_up_company(
	company: str,
	company_type: str,
	responsible: str,
	reviewer: str | None,
	registrations: list[dict],
	client: str | None = None,
	agm_dates: list[dict] | None = None,
) -> tuple[int, int]:
	"""Make the company's compliance profile, find its obligations and make its first filings;
	returns how many obligations and filings."""
	profile = frappe.get_doc(
		{
			"doctype": "Company Compliance Profile",
			"company": company,
			"client": client,
			"company_type": company_type,
			"default_responsible": responsible,
			"default_reviewer": reviewer,
			"registrations": registrations,
			"agm_dates": agm_dates or [],
		}
	).insert()
	return profile.find_obligations(), generate_tasks(company=company)


def complete(setup: dict) -> dict:
	"""Set the site up from the onboarding answers; returns what was made."""
	check_can_onboard()
	settings = scoped.settings(for_update=True)
	if settings.setup_complete:
		frappe.throw(_("The app is already set up; change these details in the Desk."))
	account_type = setup.get("account_type")
	if account_type not in ACCOUNT_TYPES:
		frappe.throw(_("Choose whether the app is for an organisation or a CA/CS firm."))
	company_type = setup.get("company_type")
	if company_type not in select_options("Company Compliance Profile", "company_type"):
		frappe.throw(_("Choose what kind of company {0} is.").format(setup.get("company") or _("this")))
	responsible = setup.get("responsible")
	if not responsible or not scoped.exists("User", responsible):
		frappe.throw(_("Choose who is responsible for the filings."))
	reviewer = setup.get("reviewer") or None
	if reviewer and not scoped.exists("User", reviewer):
		frappe.throw(_("{0} is not a user on this site.").format(reviewer))
	registrations = clean_registrations(setup.get("registrations"))
	agm_dates = (
		clean_agm_date(setup.get("agm_date"), getdate(nowdate()))
		if company_type in agm_company_types()
		else []
	)
	client_name = (setup.get("client_name") or "").strip()
	if account_type == "CA/CS Firm" and not client_name:
		frappe.throw(_("Give the name of the client this company belongs to."))

	if setup.get("new_company"):
		company = make_company(setup["new_company"])
	else:
		company = setup.get("company")
		if not company or not scoped.exists("Company", company):
			frappe.throw(_("Choose the company, or give the name of a new one."))
		if scoped.exists("Company Compliance Profile", company):
			frappe.throw(_("{0} is already set up for compliance.").format(company))

	client = None
	if account_type == "CA/CS Firm":
		client = (
			client_named(client_name)
			or frappe.get_doc(
				{
					"doctype": "Compliance Client",
					"client_name": client_name,
					"relationship_manager": frappe.session.user,
				}
			)
			.insert()
			.name
		)

	obligations, tasks = set_up_company(
		company, company_type, responsible, reviewer, registrations, client, agm_dates=agm_dates
	)

	settings.account_type = account_type
	if account_type == "CA/CS Firm" and (setup.get("firm_name") or "").strip():
		settings.app_name = setup["firm_name"].strip()
	# The privacy notice names a grievance officer; until the site names its own, the person who
	# set the app up answers, as a manager does the requests.
	if not settings.grievance_officer and not settings.grievance_email:
		settings.grievance_officer = frappe.utils.get_fullname(frappe.session.user)
		settings.grievance_email = scoped.get_value("User", frappe.session.user, "email")
	settings.setup_complete = 1
	settings.save()
	return {"company": company, "client": client, "obligations": obligations, "tasks": tasks}
