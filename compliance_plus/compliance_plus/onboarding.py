# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""First-run onboarding in the app: who the site is for, the first company (an existing
ERPNext company or a new one), its kind, registrations and people. Completing it makes the
compliance profile, finds the company's obligations in the library and makes the first tasks."""

import re

import frappe
from frappe import _

from compliance_plus.compliance_plus.register import APPROVER_ROLES
from compliance_plus.compliance_plus.statutory import generate_tasks

SETTINGS = "Compliance Plus Settings"
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


def options() -> dict:
	"""What the onboarding screens offer to choose from."""
	check_can_onboard()
	with_profile = set(frappe.get_all("Company Compliance Profile", pluck="company"))
	users = sorted(
		set(
			frappe.get_all(
				"Has Role", filters={"role": ("in", PEOPLE_ROLES), "parenttype": "User"}, pluck="parent"
			)
		)
		- {"Guest"}
	)
	people = frappe.get_all(
		"User",
		filters={"name": ("in", users), "enabled": 1, "user_type": "System User"},
		fields=["name", "full_name"],
		order_by="full_name asc",
	)
	return {
		"companies": [
			{"name": name, "set_up": name in with_profile}
			for name in frappe.get_all("Company", pluck="name", order_by="name asc")
		],
		"company_types": select_options("Company Compliance Profile", "company_type"),
		"registration_types": select_options("Compliance Registration", "registration_type"),
		"state_registrations": sorted(STATE_REGISTRATIONS),
		"states": select_options("Compliance Registration", "state"),
		"people": people,
		"can_create_company": bool(frappe.has_permission("Company", "create")),
		# ERPNext's own setup (currency, fiscal year, basic records) must be done before a
		# company can be created; running it from here is not done yet (RK, 15 Nov 2026).
		"system_ready": bool(frappe.is_setup_complete()),
	}


def company_abbr(name: str) -> str:
	"""Initials for a new company's abbreviation, numbered if another company has them."""
	initials = "".join(word[0] for word in re.findall(r"[A-Za-z0-9]+", name)).upper()[:5] or "CO"
	abbr, number = initials, 1
	while frappe.db.exists("Company", {"abbr": abbr}):
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
	if frappe.db.exists("Company", name):
		frappe.throw(_("A company named {0} already exists; choose it instead.").format(name))
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


def complete(setup: dict) -> dict:
	"""Set the site up from the onboarding answers; returns what was made."""
	check_can_onboard()
	settings = frappe.get_doc(SETTINGS)
	if settings.setup_complete:
		frappe.throw(_("The app is already set up; change these details in the Desk."))
	account_type = setup.get("account_type")
	if account_type not in ACCOUNT_TYPES:
		frappe.throw(_("Choose whether the app is for an organisation or a CA/CS firm."))
	company_type = setup.get("company_type")
	if company_type not in select_options("Company Compliance Profile", "company_type"):
		frappe.throw(_("Choose what kind of company {0} is.").format(setup.get("company") or _("this")))
	responsible = setup.get("responsible")
	if not responsible or not frappe.db.exists("User", responsible):
		frappe.throw(_("Choose who is responsible for the filings."))
	reviewer = setup.get("reviewer") or None
	if reviewer and not frappe.db.exists("User", reviewer):
		frappe.throw(_("{0} is not a user on this site.").format(reviewer))
	registrations = clean_registrations(setup.get("registrations"))
	client_name = (setup.get("client_name") or "").strip()
	if account_type == "CA/CS Firm" and not client_name:
		frappe.throw(_("Give the name of the client this company belongs to."))

	if setup.get("new_company"):
		company = make_company(setup["new_company"])
	else:
		company = setup.get("company")
		if not company or not frappe.db.exists("Company", company):
			frappe.throw(_("Choose the company, or give the name of a new one."))
		if frappe.db.exists("Company Compliance Profile", company):
			frappe.throw(_("{0} is already set up for compliance.").format(company))

	client = None
	if account_type == "CA/CS Firm":
		client = (
			client_name
			if frappe.db.exists("Compliance Client", client_name)
			else frappe.get_doc(
				{
					"doctype": "Compliance Client",
					"client_name": client_name,
					"relationship_manager": frappe.session.user,
				}
			)
			.insert()
			.name
		)

	profile = frappe.get_doc(
		{
			"doctype": "Company Compliance Profile",
			"company": company,
			"client": client,
			"company_type": company_type,
			"default_responsible": responsible,
			"default_reviewer": reviewer,
			"registrations": registrations,
		}
	).insert()
	obligations = profile.find_obligations()
	tasks = generate_tasks(company=company)

	settings.account_type = account_type
	if account_type == "CA/CS Firm" and (setup.get("firm_name") or "").strip():
		settings.app_name = setup["firm_name"].strip()
	settings.setup_complete = 1
	settings.save()
	return {"company": company, "client": client, "obligations": obligations, "tasks": tasks}
