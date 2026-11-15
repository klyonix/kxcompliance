# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Shared rules for Legal Dates and the daily job that reminds and escalates them."""

import frappe
from frappe import _
from frappe.utils import date_diff, escape_html, formatdate, getdate, nowdate

from kxcompliance.kx_compliance.register import get_settings
from kxcompliance.kx_compliance.reminders import (
	already_sent,
	compliance_managers,
	notify,
	run_for_item,
	write_log,
)

# What a Legal Date can belong to, and the field that names it.
REFERENCE_TITLES = {"Legal Case": "title", "Trademark": "mark"}
# The field that names the company a case or trademark belongs to.
REFERENCE_COMPANIES = {"Legal Case": "company", "Trademark": "applicant"}
CLOSED_CASE_STATUSES = ("Disposed - In Our Favour", "Disposed - Against Us", "Settled", "Withdrawn")
ENDED_MARK_STATUSES = ("Refused", "Abandoned", "Withdrawn", "Removed")
# What the registry sends at each stage of a trademark, recorded as it moves there; the dates
# start the trademark's deadlines (see Trademark.DEADLINES).
MARK_STATUS_FIELDS = {
	"Objected": ("examination_report_on",),
	"Accepted and Advertised": ("journal_number", "journal_date"),
	"Opposed": ("opposition_number", "opposition_notice_on"),
	"Registered": ("registration_number", "registration_date"),
}
REMINDER_DAYS = (7, 2, 1)
DATE_FIELDS = [
	"name",
	"reference_doctype",
	"reference_name",
	"reference_title",
	"kind",
	"date",
	"responsible",
	"reviewer",
]


def pass_company_to_dates(doctype: str, name: str, company: str | None):
	"""Legal Dates carry their case's or trademark's company, which permissions and lists filter by."""
	legal_date = frappe.qb.DocType("Legal Date")
	(
		frappe.qb.update(legal_date)
		.set(legal_date.company, company)
		.where((legal_date.reference_doctype == doctype) & (legal_date.reference_name == name))
	).run()


def refresh_next_date(doctype: str, name: str):
	"""Keep the case's or trademark's Next Date on its earliest scheduled step."""
	if doctype not in REFERENCE_TITLES or not frappe.db.exists(doctype, name):
		return
	dates = frappe.get_all(
		"Legal Date",
		filters={"reference_doctype": doctype, "reference_name": name, "status": "Scheduled"},
		pluck="date",
		order_by="date asc",
		limit=1,
	)
	# A shown-only summary of the steps, not a state of the record; it must not bump `modified`.
	frappe.db.set_value(doctype, name, "next_date", dates[0] if dates else None, update_modified=False)


def label(row) -> str:
	return f"{_(row.kind)}: {row.reference_title or row.reference_name}"


def run_daily():
	today = getdate(nowdate())
	refresh_overdue(today)
	if not get_settings().enabled:
		return
	send_reminders(today)
	send_escalations(today)


def refresh_overdue(today):
	rows = frappe.get_all(
		"Legal Date", filters={"status": "Scheduled"}, fields=["name", "date", "is_overdue"]
	)
	for row in rows:
		if int(getdate(row.date) < today) != row.is_overdue:
			run_for_item(row.name, lambda name=row.name: frappe.get_doc("Legal Date", name).save())


def send_reminders(today):
	rows = frappe.get_all(
		"Legal Date", filters={"status": "Scheduled", "date": (">=", today)}, fields=DATE_FIELDS
	)
	due = []
	for row in rows:
		days_left = date_diff(row.date, today)
		passed = [days for days in REMINDER_DAYS if days >= days_left]
		if passed:
			days = min(passed)
			due.append((row, days, f"{row.name}|reminder|{days}|{row.date}"))
	sent = already_sent([key for _row, _days, key in due])
	for row, days, key in due:
		if key not in sent:
			run_for_item(row.name, lambda row=row, days=days, key=key: remind(row, days, key))


def remind(row, days: int, key: str):
	subject = _("{0} on {1}").format(label(row), formatdate(row.date))
	message = _("{0} is on {1}.").format(escape_html(label(row)), formatdate(row.date))
	write_log("Reminder", key, [row.responsible], legal_date=row.name, rule_days=days, due_date=row.date)
	notify([row.responsible], subject, message, "Legal Date", row.name)


def send_escalations(today):
	rows = frappe.get_all(
		"Legal Date", filters={"status": "Scheduled", "date": ("<", today)}, fields=DATE_FIELDS
	)
	due = [(row, f"{row.name}|escalation|{row.date}") for row in rows]
	sent = already_sent([key for _row, key in due])
	managers = compliance_managers()
	for row, key in due:
		if key not in sent:
			run_for_item(row.name, lambda row=row, key=key: escalate(row, key, managers))


def escalate(row, key: str, managers: list[str]):
	recipients = [user for user in [row.reviewer, *managers] if user]
	subject = _("No outcome recorded: {0}").format(label(row))
	message = _("{0} was on {1} and nothing has been recorded since. It is held by {2}.").format(
		escape_html(label(row)), formatdate(row.date), escape_html(row.responsible)
	)
	write_log("Escalation", key, recipients, legal_date=row.name, due_date=row.date)
	notify(recipients, subject, message, "Legal Date", row.name)


def pass_people_to_dates(doctype: str, name: str, responsible: str | None, reviewer: str | None):
	"""A case's or trademark's people go on to its scheduled dates, which lists filter by."""
	legal_date = frappe.qb.DocType("Legal Date")
	(
		frappe.qb.update(legal_date)
		.set(legal_date.responsible, responsible)
		.set(legal_date.reviewer, reviewer)
		.where(
			(legal_date.reference_doctype == doctype)
			& (legal_date.reference_name == name)
			& (legal_date.status == "Scheduled")
		)
	).run()


def check_status_change(doc):
	"""Once a case or trademark exists, its status is changed by whoever holds it or reviews it, or
	by a Compliance Manager. Held here so every way of saving keeps the rule."""
	from kxcompliance.kx_compliance.register import is_approver

	if doc.is_new() or not doc.has_value_changed("status") or is_approver():
		return
	if frappe.session.user in (doc.responsible, doc.reviewer):
		return
	before = (doc.get_doc_before_save() or {}).get("status")
	frappe.throw(
		_(
			"Only whoever holds or reviews {0}, or a Compliance Manager, can change its status from {1} to {2}."
		).format(doc.name, _(before), _(doc.status)),
		frappe.PermissionError,
	)


def scheduled_dates(doctype: str, name: str) -> list[str]:
	return frappe.get_all(
		"Legal Date",
		filters={"reference_doctype": doctype, "reference_name": name, "status": "Scheduled"},
		pluck="name",
		order_by="date asc",
	)


def cancel_scheduled_dates(doctype: str, name: str, reason: str):
	"""A closed case has nothing left to attend: its scheduled hearings and deadlines are cancelled,
	so no reminder or escalation goes out for them."""
	for date_name in scheduled_dates(doctype, name):
		legal_date = frappe.get_doc("Legal Date", date_name)
		legal_date.status = "Cancelled"
		legal_date.proceedings = legal_date.proceedings or reason
		legal_date.save()
