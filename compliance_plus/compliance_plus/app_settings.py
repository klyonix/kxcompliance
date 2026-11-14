# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""The app's own settings screen: reminders, email, branding and who the site is for.

Only these fields are read and changed here, and only by Compliance Managers; the rest of
Compliance Plus Settings stays in the Desk.
"""

import frappe
from frappe import _
from frappe.utils import cint

from compliance_plus.compliance_plus.register import is_approver

SETTINGS = "Compliance Plus Settings"
FIELDS = (
	"enabled",
	"email_account",
	"due_soon_days",
	"escalate_after_days",
	"digest_day",
	"generation_horizon_days",
	"party_email_template",
	"app_name",
	"app_logo",
	"account_type",
)
# Whole numbers and the range each may take.
NUMBERS = {
	"due_soon_days": (1, 365),
	"escalate_after_days": (0, 90),
	"generation_horizon_days": (7, 180),
}


def check_manager():
	if not is_approver():
		frappe.throw(_("Only a Compliance Manager can change the app's settings."), frappe.PermissionError)


def options() -> dict:
	"""The settings, and the choices the screen offers."""
	check_manager()
	settings = frappe.get_doc(SETTINGS)
	meta = frappe.get_meta(SETTINGS)
	# Names and addresses only, for picking one; managers do not otherwise read these.
	accounts = frappe.get_all(
		"Email Account",
		filters={"enable_outgoing": 1},
		fields=["name", "email_id"],
		order_by="name asc",
	)
	templates = frappe.get_all("Email Template", pluck="name", order_by="name asc")
	return {
		"values": {field: settings.get(field) for field in FIELDS},
		"email_accounts": accounts,
		"email_templates": templates,
		"digest_days": [day for day in meta.get_field("digest_day").options.split("\n") if day],
		"account_types": [kind for kind in meta.get_field("account_type").options.split("\n") if kind],
	}


def save(values: dict) -> dict:
	"""Change the given settings; anything else in `values` is refused."""
	check_manager()
	unknown = sorted(set(values) - set(FIELDS))
	if unknown:
		frappe.throw(_("The app cannot change {0} in the settings.").format(", ".join(unknown)))
	settings = frappe.get_doc(SETTINGS)
	for field, value in values.items():
		if field in NUMBERS:
			low, high = NUMBERS[field]
			value = cint(value)
			if not low <= value <= high:
				frappe.throw(
					_("{0} should be between {1} and {2}, not {3}.").format(
						_(settings.meta.get_label(field)), low, high, value
					)
				)
		if field == "enabled":
			value = cint(value)
		settings.set(field, value)
	settings.save()
	return {field: settings.get(field) for field in FIELDS}
