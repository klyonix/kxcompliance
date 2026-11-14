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
