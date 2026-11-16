# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Records the compliance tests build for themselves."""

from contextlib import ExitStack, contextmanager
from unittest.mock import patch

import frappe
from frappe.utils import add_days, nowdate

from kxcompliance import scoped

TEST_COMPANY = "Compliance Test Company"
MANAGER = "compliance-manager@example.com"
HOLDER = "compliance-holder@example.com"
OTHER_HOLDER = "compliance-other@example.com"
AUDITOR = "compliance-auditor@example.com"
REVIEWER = "compliance-reviewer@example.com"


def before_tests():
	"""A new test site has not been through ERPNext's setup, which makes what a company needs
	(warehouse types, UOMs, fiscal year). Complete it once, as a person would in the wizard."""
	if frappe.is_setup_complete():
		return
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	setup_complete(
		{
			"language": "English",
			"country": "India",
			"timezone": "Asia/Kolkata",
			"currency": "INR",
			"company_name": "Compliance Setup Company",
			"company_abbr": "CSCO",
			"chart_of_accounts": "Standard",
			"fy_start_date": "2026-04-01",
			"fy_end_date": "2027-03-31",
		}
	)


def make_company() -> str:
	if not frappe.db.exists("Company", TEST_COMPANY):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": TEST_COMPANY,
				"abbr": "CTCO",
				"default_currency": "INR",
				"country": "India",
			}
		).insert()
	return TEST_COMPANY


def make_user(email: str, roles: tuple[str, ...]) -> str:
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
	else:
		user = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		).insert()
	user.add_roles(*roles)
	return email


def make_users():
	make_user(MANAGER, ("Compliance Manager",))
	make_user(HOLDER, ("Compliance User",))
	make_user(OTHER_HOLDER, ("Compliance User",))
	make_user(REVIEWER, ("Compliance User",))
	make_user(AUDITOR, ("Compliance Auditor",))


def make_item_type(
	name: str, *, cycle: int = 12, grace: int = 10, requires_document: int = 0, reminders=(30, 7)
):
	if frappe.db.exists("Compliance Item Type", name):
		frappe.delete_doc("Compliance Item Type", name, force=True)
	return frappe.get_doc(
		{
			"doctype": "Compliance Item Type",
			"type_name": name,
			"category": "Licence",
			"renewal_cycle_months": cycle,
			"grace_days": grace,
			"requires_document": requires_document,
			"reminders": [{"days_before": days} for days in reminders],
		}
	).insert()


def make_item(item_type: str, *, valid_until=None, days: int | None = 200, **fields):
	if valid_until is None and days is not None:
		valid_until = add_days(nowdate(), days)
	doc = frappe.get_doc(
		{
			"doctype": "Compliance Item",
			"title": fields.pop("title", "Test licence"),
			"item_type": item_type,
			"company": TEST_COMPANY,
			"valid_until": valid_until,
			"responsible": fields.pop("responsible", HOLDER),
			**fields,
		}
	)
	return doc.insert()


def make_file(name: str = "certificate.txt") -> str:
	return (
		frappe.get_doc(
			{"doctype": "File", "file_name": name, "content": b"test certificate", "is_private": 1}
		)
		.insert()
		.file_url
	)


@contextmanager
def named_by_id(*doctypes: str):
	"""These doctypes named by a hidden ID rather than their title, as a site hosting many firms
	names clients and rate cards, so a test can check nothing takes the ID for the title. Frappe
	asks a controller's own autoname first; nothing is saved, so a commit leaves nothing behind."""
	from frappe.model.base_document import get_controller
	from frappe.model.naming import make_autoname

	def by_id(doc):
		doc.name = make_autoname("hash", doc.doctype)

	def keep_title(doc):
		"""Named by ID, the title is not copied from the name as a field-named record's is."""

	with ExitStack() as stack:
		for doctype in doctypes:
			controller = get_controller(doctype)
			stack.enter_context(patch.object(controller, "autoname", by_id, create=True))
			stack.enter_context(patch.object(controller, "_sync_autoname_field", keep_title))
		yield


# The app's settings, wherever this site keeps them: KX Compliance Settings, or the record another
# app supplies (kxcompliance_settings), so the tests run on both kinds of site.
def app_settings():
	"""The settings as saved, read fresh."""
	return scoped.settings(for_update=True)


def app_setting(fieldname: str):
	return app_settings().get(fieldname)


def set_app_settings(values: dict | None = None, /, **more):
	"""Write settings straight to the database, without the settings' own checks."""
	values = {**(values or {}), **more}
	record = scoped.settings_record()
	if record["doctype"] == record["name"]:
		frappe.db.set_single_value(record["doctype"], values)
	else:
		frappe.db.set_value(record["doctype"], record["name"], values)
	frappe.clear_document_cache(record["doctype"], record["name"])


@contextmanager
def change_app_settings(values: dict | None = None, /, **more):
	"""Saved through the settings' own checks for the length of the block, as Frappe's
	change_settings does for a single doctype."""
	values = {**(values or {}), **more}
	settings = app_settings()
	before = {fieldname: settings.get(fieldname) for fieldname in values}
	settings.update(values)
	settings.save(ignore_permissions=True)
	try:
		yield
	finally:
		settings = app_settings()
		settings.update(before)
		settings.save(ignore_permissions=True)
