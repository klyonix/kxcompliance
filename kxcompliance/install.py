# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe

from kxcompliance.kx_compliance.obligation_library import sync_standard_templates

ROLES = ("Compliance Manager", "Compliance User", "Compliance Auditor")
# A CA/CS firm's client who signs in to the app only; without Desk access Frappe makes them
# a Website User.
CLIENT_ROLE = "Compliance Client"

# (name, category, renewal cycle in months or 0 if it does not expire, grace days,
#  certificate required, reminder days)
STANDARD_ITEM_TYPES = (
	("Shops and Establishment Registration", "Registration", 12, 30, 1, (60, 30, 7)),
	("Trade Licence", "Licence", 12, 30, 1, (60, 30, 7)),
	("Fire NOC", "Certificate", 12, 0, 1, (90, 30, 7)),
	("Pollution Consent (CTE/CTO)", "Licence", 60, 0, 1, (120, 60, 30)),
	("Factory Licence", "Licence", 12, 0, 1, (90, 30, 7)),
	("Drug Licence", "Licence", 60, 0, 1, (90, 30, 7)),
	("FSSAI Licence", "Licence", 12, 0, 1, (60, 30, 7)),
	("Professional Tax Registration", "Registration", 0, 0, 1, ()),
	("ISO Certificate", "Certificate", 36, 0, 1, (90, 30)),
	("Digital Signature Certificate", "Certificate", 24, 0, 0, (30, 7, 1)),
	("Group Health Insurance", "Insurance", 12, 0, 1, (60, 30, 7)),
	("Fire Insurance", "Insurance", 12, 0, 1, (60, 30, 7)),
	("Software Subscription", "Subscription", 12, 0, 0, (30, 7)),
	("Domain and SSL", "Subscription", 12, 0, 0, (30, 7, 1)),
	("Annual Maintenance Contract", "Contract", 12, 0, 1, (60, 30)),
)

SETTINGS_DEFAULTS = {
	"due_soon_days": 30,
	"escalate_after_days": 7,
	"digest_day": "Monday",
	"generation_horizon_days": 45,
}


def after_install():
	setup()
	sync_standard_templates()


def after_migrate():
	try:
		sync_standard_templates()
	except Exception as error:
		raise Exception(
			f"KlyONIX Compliance could not update its standard obligation library: {error}"
		) from error


def setup():
	create_roles()
	create_standard_item_types()
	set_settings_defaults()


def create_roles():
	for role in ROLES:
		create_role(role, desk_access=1)
	create_role(CLIENT_ROLE, desk_access=0)


def create_role(role: str, desk_access: int):
	if frappe.db.exists("Role", role):
		return
	frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": desk_access}).insert(
		ignore_permissions=True  # setup record created during install or migrate
	)


def create_standard_item_types():
	for name, category, cycle, grace, requires_document, reminders in STANDARD_ITEM_TYPES:
		if frappe.db.exists("Compliance Item Type", name):
			continue
		frappe.get_doc(
			{
				"doctype": "Compliance Item Type",
				"type_name": name,
				"category": category,
				"renewal_cycle_months": cycle,
				"grace_days": grace,
				"requires_document": requires_document,
				"reminders": [{"days_before": days} for days in reminders],
			}
		).insert(ignore_permissions=True)  # setup record created during install or migrate


def set_settings_defaults():
	stored = frappe.db.get_singles_dict("KX Compliance Settings", cast=False)
	for fieldname, value in SETTINGS_DEFAULTS.items():
		if stored.get(fieldname) in (None, ""):
			frappe.db.set_single_value("KX Compliance Settings", fieldname, value)
