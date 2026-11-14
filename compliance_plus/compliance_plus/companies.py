# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Companies in the app: which are set up for compliance, and setting one up or changing it.

Setting a company up works as onboarding and bulk setup do. Changing one takes only the fields
the screen shows: its kind, client, people, registrations, and per obligation whether it
applies and who handles it. New registrations bring their obligations from the library and
their first filings, as finding obligations does in the Desk.
"""

import frappe
from frappe import _
from frappe.utils import cint

from compliance_plus.compliance_plus.onboarding import (
	STATE_REGISTRATIONS,
	clean_registrations,
	firm_people,
	make_company,
	select_options,
	set_up_company,
)
from compliance_plus.compliance_plus.register import is_approver
from compliance_plus.compliance_plus.statutory import generate_tasks

PROFILE = "Company Compliance Profile"
COUNT = {"COUNT": "*", "as": "count"}


def check_manager():
	if not is_approver():
		frappe.throw(_("Only a Compliance Manager can set companies up."), frappe.PermissionError)


def companies_overview() -> dict:
	"""The companies set up for compliance, and ERPNext companies that are not yet."""
	check_manager()
	profiles = frappe.get_list(
		PROFILE, fields=["company", "company_type", "client"], order_by="company asc", limit=1000
	)
	names = [row.company for row in profiles] or [""]
	registrations = counts_by_parent("Compliance Registration", names)
	obligations = counts_by_parent("Company Obligation", names, {"is_active": 1})
	for row in profiles:
		row.registrations = registrations.get(row.company, 0)
		row.obligations = obligations.get(row.company, 0)
	set_up = {row.company for row in profiles}
	return {
		"companies": profiles,
		"not_set_up": [
			name
			for name in frappe.get_all("Company", pluck="name", order_by="name asc")
			if name not in set_up
		],
	}


def counts_by_parent(doctype: str, parents: list[str], filters: dict | None = None) -> dict[str, int]:
	rows = frappe.get_all(
		doctype,
		filters={"parenttype": PROFILE, "parent": ("in", parents), **(filters or {})},
		fields=["parent", COUNT],
		group_by="parent",
	)
	return {row.parent: row["count"] for row in rows}


def form_options() -> dict:
	"""What the company screen offers to choose from."""
	check_manager()
	set_up = set(frappe.get_all(PROFILE, pluck="company"))
	return {
		"company_types": select_options(PROFILE, "company_type"),
		"registration_types": select_options("Compliance Registration", "registration_type"),
		"state_registrations": sorted(STATE_REGISTRATIONS),
		"states": select_options("Compliance Registration", "state"),
		"not_set_up": [
			name
			for name in frappe.get_all("Company", pluck="name", order_by="name asc")
			if name not in set_up
		],
		"people": firm_people(),
		"clients": frappe.get_list("Compliance Client", filters={"status": ("!=", "Left")}, pluck="name"),
		"can_create_company": bool(frappe.has_permission("Company", "create"))
		and bool(frappe.is_setup_complete()),
	}


def company_detail(company: str) -> dict:
	"""A company's compliance profile, with each obligation's law and how often it falls due."""
	check_manager()
	profile = frappe.get_doc(PROFILE, company)
	profile.check_permission("read")
	templates = {
		row.name: row
		for row in frappe.get_all(
			"Compliance Obligation Template",
			filters={"name": ("in", [row.obligation_template for row in profile.obligations] or [""])},
			fields=["name", "law", "frequency"],
		)
	}
	return {
		"company": profile.company,
		"company_type": profile.company_type,
		"client": profile.client,
		"default_responsible": profile.default_responsible,
		"default_reviewer": profile.default_reviewer,
		"registrations": [
			{
				"registration_type": row.registration_type,
				"registration_number": row.registration_number,
				"state": row.state,
			}
			for row in profile.registrations
		],
		"obligations": [
			{
				"name": row.name,
				"obligation_template": row.obligation_template,
				"law": (templates.get(row.obligation_template) or {}).get("law"),
				"frequency": (templates.get(row.obligation_template) or {}).get("frequency"),
				"registration_number": row.registration_number,
				"state": row.state,
				"responsible": row.responsible,
				"reviewer": row.reviewer,
				"is_active": row.is_active,
			}
			for row in profile.obligations
		],
		"modified": str(profile.modified),
	}


def check_person(user: str | None, label: str):
	if user and user not in {person.name for person in firm_people()}:
		frappe.throw(_("{0} {1} is not someone who can be given compliance work.").format(label, user))


def save_company(company: str, values: dict, new_company: bool = False) -> dict:
	"""Set a company up, or change its profile; returns what was made or changed."""
	check_manager()
	company = (company or "").strip()
	if not company:
		frappe.throw(_("Give the company's name."))
	company_type = values.get("company_type")
	if company_type not in select_options(PROFILE, "company_type"):
		frappe.throw(_("Choose what kind of company {0} is.").format(company))
	responsible = values.get("default_responsible")
	if not responsible:
		frappe.throw(_("Choose who is responsible for {0}'s filings.").format(company))
	check_person(responsible, _("Responsible"))
	check_person(values.get("default_reviewer"), _("Reviewer"))
	client = values.get("client") or None
	if client and not frappe.has_permission("Compliance Client", "read", doc=client):
		frappe.throw(_("You cannot choose the client {0}.").format(client), frappe.PermissionError)
	registrations = clean_registrations(values.get("registrations"))

	if not frappe.db.exists(PROFILE, company):
		if new_company:
			company = make_company(company)
		elif not frappe.db.exists("Company", company):
			frappe.throw(_("{0} is not a company here; add it as a new company.").format(company))
		obligations, tasks = set_up_company(
			company, company_type, responsible, values.get("default_reviewer"), registrations, client
		)
		return {"company": company, "obligations": obligations, "tasks": tasks}

	profile = frappe.get_doc(PROFILE, company)
	profile.check_permission("write")
	profile.company_type = company_type
	profile.client = client
	profile.default_responsible = responsible
	profile.default_reviewer = values.get("default_reviewer") or None
	profile.set("registrations", registrations)
	update_obligations(profile, values.get("obligations") or [])
	profile.save()
	# New registrations bring their obligations and first filings.
	obligations = profile.find_obligations()
	return {"company": company, "obligations": obligations, "tasks": generate_tasks(company=company)}


def update_obligations(profile, changes: list):
	"""Per obligation row: whether it applies, and who handles it; nothing else is taken."""
	rows = {row.name: row for row in profile.obligations}
	for change in changes:
		row = rows.get(change.get("name"))
		if not row:
			frappe.throw(
				_("{0} is not one of {1}'s obligations.").format(change.get("name"), profile.company)
			)
		check_person(change.get("responsible"), _("Responsible"))
		check_person(change.get("reviewer"), _("Reviewer"))
		row.is_active = cint(change.get("is_active"))
		row.responsible = change.get("responsible") or None
		row.reviewer = change.get("reviewer") or None
