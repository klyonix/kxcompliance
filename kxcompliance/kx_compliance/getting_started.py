# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""The first-week checklist on a manager's My Work: the few things that make the app useful,
each ticked off by itself once done. A manager may hide it; it goes once everything is done.
"""

import frappe
from frappe import _

from kxcompliance.install import ROLES
from kxcompliance.kx_compliance.register import get_settings, is_approver

HIDDEN = "kxcompliance_getting_started_hidden"


def is_firm() -> bool:
	return get_settings().account_type == "CA/CS Firm"


def colleagues() -> int:
	"""Other enabled people on the team besides the person asking and the Administrator."""
	users = set(
		frappe.get_all("Has Role", filters={"role": ("in", ROLES), "parenttype": "User"}, pluck="parent")
	) - {frappe.session.user, "Administrator", "Guest"}
	if not users:
		return 0
	return frappe.db.count("User", {"name": ("in", list(users)), "enabled": 1})


def checklist() -> dict:
	if not is_approver():
		return {"show": False, "steps": []}
	settings = get_settings()
	steps = [
		{
			"key": "company",
			"label": _("Set up a company"),
			"detail": _("Its kind, registrations and people, so the calendar starts making filings."),
			"done": bool(frappe.db.count("Company Compliance Profile")),
		},
		*(
			[
				{
					"key": "client",
					"label": _("Add a client"),
					"detail": _("The client, its companies and the team who looks after it."),
					"done": bool(frappe.db.count("Compliance Client")),
				}
			]
			if is_firm()
			else []
		),
		{
			"key": "colleague",
			"label": _("Invite a colleague"),
			"detail": _("Someone else to hold or review work, so filings get a second look."),
			"done": colleagues() > 0,
		},
		*(
			[
				{
					"key": "billing",
					"label": _("Set up billing"),
					"detail": _("The firm's GSTIN, bank details and rates, so filed work turns into bills."),
					"done": bool(settings.billing_company),
				}
			]
			if is_firm()
			else []
		),
		{
			"key": "privacy",
			"label": _("Name your grievance officer"),
			"detail": _("The person and email the privacy notice gives for questions about personal data."),
			"done": bool(settings.grievance_officer and settings.grievance_email),
		},
		{
			"key": "reminders",
			"label": _("Turn on reminders"),
			"detail": _("Choose the email account and switch reminders on, so nothing is missed."),
			"done": bool(settings.enabled and settings.email_account),
		},
	]
	hidden = bool(frappe.defaults.get_user_default(HIDDEN))
	return {"show": not hidden and not all(step["done"] for step in steps), "steps": steps}


def hide():
	"""Stop showing the checklist to this person."""
	frappe.defaults.set_user_default(HIDDEN, 1)
