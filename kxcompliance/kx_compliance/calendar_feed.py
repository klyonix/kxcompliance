# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Each person's compliance calendar as a feed that Google Calendar or Outlook subscribes to.

A calendar app cannot sign in, so the feed's link carries a secret. Only its hash is looked up,
and resetting it stops the old link at once. The feed is built with the person's own
permissions, so it never shows what they could not see in the app: by default their own work
(what they hold or review); for managers, if they choose, everything they can see; and for a
client's login, its companies' filings and the documents the firm has asked for.
"""

import hashlib
import secrets
from datetime import datetime

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, get_datetime, get_url, getdate, nowdate
from frappe.utils.password import get_decrypted_password

from kxcompliance.api import can_open_app, has_app_access, is_client_login
from kxcompliance.kx_compliance.ical import calendar
from kxcompliance.kx_compliance.register import CLOSED_TASK_STATUSES, get_settings, is_approver

FEED = "Compliance Calendar Feed"
SCOPES = ("My Work", "Everything I Can See")
DAYS_AHEAD = 365
LIMIT = 500


def digest(token: str) -> str:
	return hashlib.sha256(token.encode()).hexdigest()


def feed_url(token: str) -> str:
	return get_url(f"/api/method/kxcompliance.kx_compliance.calendar_feed.feed?token={token}")


def check_may_have_feed():
	if frappe.session.user == "Guest" or not (has_app_access() or is_client_login()):
		frappe.throw(_("You do not have access to the compliance app."), frappe.PermissionError)


def own_feed():
	"""The signed-in person's feed record, if they have one."""
	name = frappe.db.exists(FEED, {"user": frappe.session.user})
	return frappe.get_doc(FEED, name) if name else None


def answer(record) -> dict:
	if not record:
		return {"url": "", "scope": "My Work", "may_choose_scope": is_approver()}
	token = get_decrypted_password(FEED, record.name, "token")
	return {"url": feed_url(token), "scope": record.scope, "may_choose_scope": is_approver()}


@frappe.whitelist(methods=["GET"])
def feed_settings() -> dict:
	"""The person's feed link and what it shows; an empty link if they have none yet."""
	check_may_have_feed()
	return answer(own_feed())


@frappe.whitelist(methods=["POST"])
def set_up_feed(scope: str = "My Work", new_link: bool = False) -> dict:
	"""Make the person's feed (or change what it shows); a new link stops the old one."""
	check_may_have_feed()
	if scope not in SCOPES:
		frappe.throw(_("Choose what the calendar shows: {0}.").format(", ".join(SCOPES)))
	if scope != "My Work" and not is_approver():
		frappe.throw(
			_("Only a Compliance Manager can show everything in a calendar."), frappe.PermissionError
		)
	record = own_feed() or frappe.new_doc(FEED, user=frappe.session.user)
	record.scope = scope
	if record.is_new() or new_link:
		token = secrets.token_urlsafe(32)
		record.token = token
		record.token_hash = digest(token)
	# A person's own feed: the doctype is kept out of everyone's reach but System Managers'.
	record.save(ignore_permissions=True)
	return answer(record)


@frappe.whitelist(methods=["POST"])
def stop_feed():
	"""Delete the person's feed; its link stops working."""
	check_may_have_feed()
	record = own_feed()
	if record:
		frappe.delete_doc(FEED, record.name, ignore_permissions=True)  # the person's own feed


# A calendar app cannot sign in: the secret link's token is the credential, checked below and
# rate-limited; the feed is then built with the token owner's own permissions.
@frappe.whitelist(allow_guest=True, methods=["GET"])  # nosemgrep
@rate_limit(limit=120, seconds=60 * 60)
def feed(token: str):
	"""The calendar itself, for a calendar app holding the secret link."""
	if not isinstance(token, str) or len(token) < 32:
		raise frappe.PermissionError
	record = frappe.db.get_value(FEED, {"token_hash": digest(token)}, ["user", "scope"], as_dict=True)
	if not record or not frappe.db.get_value("User", record.user, "enabled"):
		raise frappe.PermissionError
	previous = frappe.session.user
	try:
		# Build it as the person, so their own permissions decide what it shows.
		frappe.set_user(record.user)  # nosemgrep
		if not can_open_app(record.user):
			raise frappe.PermissionError
		events = events_for(record.user, record.scope)
		name = get_settings().app_name or "KlyONIX Compliance"
		text = calendar(name, events, frappe.utils.get_system_timezone())
	finally:
		frappe.set_user(previous)  # nosemgrep
	frappe.response.filename = "compliance.ics"
	frappe.response.filecontent = text
	# Served as a calendar, shown rather than saved, which is what calendar apps expect.
	frappe.response.type = "download"
	frappe.response.content_type = "text/calendar"
	frappe.response.display_content_as = "inline"


def events_for(user: str, scope: str, today: str | None = None) -> list[dict]:
	today = getdate(today or nowdate())
	until = add_days(today, DAYS_AHEAD)
	mine = {"responsible": user, "reviewer": user} if scope == "My Work" else None
	# Overdue filings, hearings and requests are kept in, on the day they fell due.
	if is_client_login(user):
		return filing_events(until, None) + request_events(until, {})
	events = filing_events(until, mine)
	events += item_events(today, until, mine)
	events += legal_events(until, mine)
	asked = {"requested_by": user} if scope == "My Work" else {}
	events += request_events(until, asked)
	return events


def app_link(path: str) -> str:
	return get_url(f"/compliance/{path}")


def uid(doctype: str, name: str) -> str:
	return f"{frappe.scrub(doctype)}-{name}@{frappe.local.site}"


def filing_events(until, mine) -> list[dict]:
	rows = frappe.get_list(
		"Compliance Task",
		filters={"status": ("not in", CLOSED_TASK_STATUSES), "effective_due_date": ("<=", until)},
		or_filters=mine,
		fields=["name", "obligation_template", "period_label", "company", "is_overdue", "effective_due_date"],
		order_by="effective_due_date asc",
		limit=LIMIT,
	)
	return [
		{
			"uid": uid("Compliance Task", row.name),
			"start": getdate(row.effective_due_date),
			"summary": filing_title(row),
			"description": _("Filing due for {0}.").format(row.company),
			"url": app_link(f"filings/{row.name}"),
		}
		for row in rows
	]


def filing_title(row) -> str:
	title = f"{row.obligation_template} ({row.period_label}) · {row.company}"
	return _("Overdue: {0}").format(title) if row.is_overdue else title


def item_events(today, until, mine) -> list[dict]:
	"""Expiries in the coming year, and those in the last 90 days not yet renewed."""
	rows = frappe.get_list(
		"Compliance Item",
		filters={"is_cancelled": 0, "valid_until": ("between", [add_days(today, -90), until])},
		or_filters=mine,
		fields=["name", "title", "item_type", "company", "valid_until"],
		order_by="valid_until asc",
		limit=LIMIT,
	)
	return [
		{
			"uid": uid("Compliance Item", row.name),
			"start": getdate(row.valid_until),
			"summary": _("Expires: {0}").format(row.title),
			"description": f"{row.item_type} · {row.company}",
			"url": app_link(f"register/{row.name}"),
		}
		for row in rows
	]


def legal_events(until, mine) -> list[dict]:
	rows = frappe.get_list(
		"Legal Date",
		filters={"status": "Scheduled", "date": ("<=", until)},
		or_filters=mine,
		fields=["name", "kind", "date", "time", "reference_doctype", "reference_name", "reference_title"],
		order_by="date asc",
		limit=LIMIT,
	)
	pages = {"Legal Case": "legal/case", "Trademark": "legal/trademark"}
	return [
		{
			"uid": uid("Legal Date", row.name),
			"start": (
				datetime.combine(getdate(row.date), get_datetime(f"2000-01-01 {row.time}").time())
				if row.time
				else getdate(row.date)
			),
			"summary": f"{row.kind}: {row.reference_title or row.reference_name}",
			"url": app_link(f"{pages.get(row.reference_doctype, 'legal')}/{row.reference_name}"),
		}
		for row in rows
	]


def request_events(until, filters: dict) -> list[dict]:
	rows = frappe.get_list(
		"Document Request",
		filters={"status": "Requested", "due_date": ("<=", until), **filters},
		fields=["name", "title", "company", "due_date"],
		order_by="due_date asc",
		limit=LIMIT,
	)
	return [
		{
			"uid": uid("Document Request", row.name),
			"start": getdate(row.due_date),
			"summary": _("Document: {0} · {1}").format(row.title, row.company),
			"url": app_link(f"requests/{row.name}"),
		}
		for row in rows
	]
