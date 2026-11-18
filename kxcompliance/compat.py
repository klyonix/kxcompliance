# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""What differs between Frappe 15 and 16, kept in one place so the app runs on both."""

import frappe
from pypika.terms import Criterion

FRAPPE_MAJOR = int(frappe.__version__.split(".")[0])

# The Desk's address: /desk from Frappe 16, /app before it.
DESK = "/desk" if FRAPPE_MAJOR >= 16 else "/app"


def pdf_of(html: str) -> bytes:
	"""HTML printed as a PDF through Chrome, as the app's bills are: built into Frappe 16, and
	the server's own Chrome or Chromium on Frappe 15 (chrome_pdf)."""
	if FRAPPE_MAJOR >= 16:
		from frappe.utils.pdf import get_chrome_pdf

		return get_chrome_pdf(None, html, {}, None, pdf_generator="chrome")
	return chrome_pdf(None, html, {}, None, pdf_generator="chrome")


# Where Chrome or Chromium is usually found; site config "chrome_path" names another.
BROWSERS = (
	"chromium",
	"chromium-browser",
	"google-chrome",
	"google-chrome-stable",
	"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
	"/Applications/Chromium.app/Contents/MacOS/Chromium",
)
PDF_TIMEOUT = 60


def chrome_pdf(print_format=None, html=None, options=None, output=None, pdf_generator=None):
	"""Frappe 15's pdf_generator hook: prints the app's bills and receipts (their print formats
	ask for "chrome") with the server's headless Chrome, as Frappe 16 does. Others get None, so
	Frappe uses wkhtmltopdf for them as before."""
	if FRAPPE_MAJOR >= 16 or pdf_generator != "chrome":
		return None
	import shutil
	import subprocess
	import tempfile
	from pathlib import Path

	browser = frappe.conf.get("chrome_path") or next(filter(None, map(shutil.which, BROWSERS)), None)
	if not browser:
		frappe.throw(
			frappe._(
				"Printing bills needs Chrome or Chromium on the server: install it, or name it as chrome_path in the site config."
			)
		)
	# Images and styles named from the site's root load from the site itself.
	page = html.replace("<head>", f'<head><base href="{frappe.utils.get_url()}/">', 1)
	with tempfile.TemporaryDirectory() as folder:
		source, pdf = Path(folder, "print.html"), Path(folder, "print.pdf")
		source.write_text(page, encoding="utf-8")
		subprocess.run(
			[
				browser,
				"--headless=new",
				"--disable-gpu",
				"--no-pdf-header-footer",
				f"--user-data-dir={Path(folder, 'profile')}",
				f"--print-to-pdf={pdf}",
				source.as_uri(),
			],
			check=True,
			capture_output=True,
			timeout=PDF_TIMEOUT,
		)
		return pdf.read_bytes()


def in_test() -> bool:
	"""Whether tests are running: frappe.in_test from Frappe 16, a flag before it."""
	return bool(getattr(frappe, "in_test", frappe.flags.in_test))


# An aggregate in a list's fields: a dict from Frappe 16, SQL text before it.
AGGREGATES = ("COUNT", "SUM", "MIN", "MAX", "AVG")


def agg(function: str, field: str, alias: str) -> dict | str:
	"""An aggregate field for get_list or get_query, such as agg("SUM", "late_fee", "late_fee")."""
	if function not in AGGREGATES or not (field == "*" or field.replace("_", "").isalnum()):
		raise ValueError(f"Not an aggregate the app uses: {function}({field})")
	if FRAPPE_MAJOR >= 16:
		return {function: field, "as": alias}
	return f"{function.lower()}({field}) as {alias}"


def get_query(doctype: str, *, ignore_permissions: bool = True, **kwargs):
	"""frappe.qb.get_query, also narrowed to what the person may read on Frappe 15, whose query
	builder has no permissions: there the conditions get_list applies are added."""
	if FRAPPE_MAJOR >= 16:
		return frappe.qb.get_query(doctype, ignore_permissions=ignore_permissions, **kwargs)
	query = frappe.qb.get_query(doctype, **kwargs)
	if not ignore_permissions:
		from frappe.desk.reportview import build_match_conditions

		# Frappe's own conditions for this person, as get_list adds them.
		condition = build_match_conditions(doctype)
		if condition:
			query = query.where(FrappeCondition(condition))
	return query


class FrappeCondition(Criterion):
	"""A permission condition Frappe 15 builds as SQL text (its own, escaped by Frappe), to join
	a query built with the query builder."""

	def __init__(self, sql: str):
		super().__init__()
		self.sql = sql

	def get_sql(self, **kwargs) -> str:
		return f"({self.sql})"


# Fields Frappe 16 masks for all but the roles allowed to see them (the doctypes' "mask"
# settings); test_compat keeps this in step with the doctype files.
MASKED = {"Signatory": {"fields": ("pan", "mobile"), "roles": ("System Manager", "Compliance Manager")}}


def keep_masked_fields_to_their_roles():
	"""Frappe 15 cannot mask a field, so there such a field is hidden instead from everyone but
	the roles that would see it unmasked: a higher permission level that only they read and
	write. Run after install and every migrate; it changes nothing on Frappe 16."""
	if FRAPPE_MAJOR >= 16:
		return
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter
	from frappe.permissions import add_permission, update_permission_property

	for doctype, masked in MASKED.items():
		for field in masked["fields"]:
			make_property_setter(doctype, field, "permlevel", 1, "Int", validate_fields_for_doctype=False)
		for role in masked["roles"]:
			if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 1}):
				add_permission(doctype, role, 1)
			update_permission_property(doctype, role, 1, "write", 1, validate=False)


APP_MENU_ITEM = {"item_label": "KlyONIX Compliance", "item_type": "Route", "route": "/compliance"}


def add_the_app_to_the_user_menu():
	"""Frappe 15's Desk has no app switcher, so the app is put first in the user menu instead.
	Navbar Settings is seeded only when Frappe is installed, so this runs after install and
	every migrate; it changes nothing on Frappe 16 or when the item is already there."""
	if FRAPPE_MAJOR >= 16:
		return
	navbar = frappe.get_single("Navbar Settings")
	if any(row.route == APP_MENU_ITEM["route"] for row in navbar.settings_dropdown):
		return
	navbar.append("settings_dropdown", APP_MENU_ITEM)
	rows = navbar.settings_dropdown
	navbar.settings_dropdown = [rows[-1], *rows[:-1]]
	for idx, row in enumerate(navbar.settings_dropdown, start=1):
		row.idx = idx
	navbar.save()
