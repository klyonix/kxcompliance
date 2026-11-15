# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Links in emails open the record in the app at /compliance, not in the Desk (RK, 15 Nov 2026).

The paths match the app's router (frontend/src/router.js); test_app_links holds them to it.
"""

from urllib.parse import quote

from frappe.utils import get_url, get_url_to_form

APP = "/compliance"
# The page of each record type in the app.
PAGES = {
	"Compliance Item": "register/{name}",
	"Compliance Task": "filings/{name}",
	"Legal Case": "legal/case/{name}",
	"Trademark": "legal/trademark/{name}",
	"Document Request": "requests/{name}",
	"Compliance Client": "clients/{name}",
	"Signatory": "signatories/{name}",
	"Privacy Request": "settings/privacy-requests/{name}",
	"Personal Data Breach": "settings/breaches/{name}",
}
# Record types shown in a list of the app rather than a page of their own.
LISTS = {"Legal Date": "legal", "Licence Check Log": "licence-check/blocks"}


def app_path(doctype: str, name: str | None) -> str | None:
	"""The record's address in the app, or None when the app does not show it."""
	if doctype in PAGES and name:
		return f"{APP}/{PAGES[doctype].format(name=quote(str(name), safe=''))}"
	if doctype in LISTS:
		return f"{APP}/{LISTS[doctype]}"
	return None


def app_url(doctype: str, name: str) -> str:
	"""Full link to the record in the app, else its Desk form."""
	path = app_path(doctype, name)
	return get_url(path) if path else get_url_to_form(doctype, name)


def point_notification_to_app(doc, method=None):
	"""Notification Log.before_insert: its email links to the app, not the Desk.

	Frappe's notification email uses the log's `link` when it has one and the Desk form when not,
	so a record the app shows gets its app address. A link set by whoever made the log is kept.
	"""
	if doc.link or not doc.document_type:
		return
	path = app_path(doc.document_type, doc.document_name)
	if path:
		doc.link = get_url(path)
