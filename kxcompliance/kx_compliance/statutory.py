# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Periods, due dates and task generation for the statutory calendar."""

import calendar
from datetime import date

import frappe
from frappe import _
from frappe.utils import add_days, add_months, date_diff, escape_html, formatdate, getdate, nowdate

from kxcompliance.kx_compliance.register import CLOSED_TASK_STATUSES, escalate_after_days, get_settings
from kxcompliance.kx_compliance.reminders import (
	already_sent,
	compliance_managers,
	notify,
	relationship_managers,
	run_for_item,
	write_log,
)

MONTHS_IN = {"Monthly": 1, "Quarterly": 3, "Half-yearly": 6, "Yearly": 12}
FIRST_MONTH = {"Financial Year": 4, "Calendar Year": 1}
DEFAULT_HORIZON_DAYS = 45


def horizon_days() -> int:
	value = get_settings().generation_horizon_days
	return DEFAULT_HORIZON_DAYS if value is None else value


def periods(frequency: str, basis: str, start: date, end: date) -> list[tuple[date, date]]:
	"""Every period of this frequency that ends on or after `start` and on or before `end`."""
	length = MONTHS_IN[frequency]
	offset = (start.month - FIRST_MONTH[basis]) % length
	current = getdate(add_months(date(start.year, start.month, 1), -offset))
	result = []
	while True:
		period_end = getdate(add_days(add_months(current, length), -1))
		if period_end > end:
			return result
		if period_end >= start:
			result.append((current, period_end))
		current = getdate(add_months(current, length))


def due_date(template, period_end: date) -> date:
	months_after, day = template.months_after_period or 0, template.due_day
	for override in template.overrides:
		if override.period_end_month == period_end.month:
			months_after, day = override.months_after_period or 0, override.due_day
	target = getdate(add_months(date(period_end.year, period_end.month, 1), months_after))
	last_day = calendar.monthrange(target.year, target.month)[1]
	return date(target.year, target.month, min(day, last_day))


def period_label(frequency: str, basis: str, period_start: date) -> str:
	if frequency == "Monthly":
		return period_start.strftime("%b %Y")
	if basis == "Financial Year":
		first = period_start.year if period_start.month >= 4 else period_start.year - 1
		year = f"{first}-{str(first + 1)[-2:]}"
		index = ((period_start.month - 4) % 12) // MONTHS_IN[frequency] + 1
	else:
		year = str(period_start.year)
		index = (period_start.month - 1) // MONTHS_IN[frequency] + 1
	if frequency == "Quarterly":
		return f"Q{index} {year}"
	if frequency == "Half-yearly":
		return f"H{index} {year}"
	return f"FY {year}" if basis == "Financial Year" else year


def task_key(template: str, company: str, registration: str | None, period_end: date) -> str:
	return f"{template}|{company}|{registration or ''}|{period_end}"


def extensions_for(templates: list[str]) -> list[frappe._dict]:
	if not templates:
		return []
	return frappe.get_all(
		"Compliance Due Date Extension",
		filters={"obligation_template": ("in", list(set(templates)))},
		fields=["name", "obligation_template", "periods_ending_from", "periods_ending_to", "new_due_date"],
		order_by="new_due_date desc",
	)


def find_extension(extensions: list[frappe._dict], template: str, period_end: date) -> frappe._dict | None:
	"""The latest extension covering this period, if any."""
	for extension in extensions:
		if extension.obligation_template == template and getdate(
			extension.periods_ending_from
		) <= period_end <= getdate(extension.periods_ending_to):
			return extension
	return None


def candidate_tasks(profile, today: date) -> list[dict]:
	"""The tasks a company's profile calls for up to the horizon, whether or not they exist yet."""
	limit = getdate(add_days(today, horizon_days()))
	agm_dates = {getdate(row.financial_year_end): getdate(row.agm_date) for row in profile.agm_dates}
	candidates = []
	for obligation in profile.obligations:
		if not obligation.is_active:
			continue
		template = frappe.get_cached_doc("Compliance Obligation Template", obligation.obligation_template)
		# Event templates are made when the event is recorded (company_events.py), not by period.
		if not template.is_active or template.event_type:
			continue
		registration = obligation.registration_number or obligation.state
		for period_start, period_end in obligation_periods(template, obligation, limit, agm_dates):
			due = (
				getdate(add_days(agm_dates[period_end], template.days_after_event))
				if template.due_after_event
				else due_date(template, period_end)
			)
			candidates.append(
				{
					"doctype": "Compliance Task",
					"obligation_template": template.name,
					"company": profile.company,
					"registration_number": obligation.registration_number,
					"state": obligation.state,
					"period_start": period_start,
					"period_end": period_end,
					"period_label": period_label(template.frequency, template.period_basis, period_start),
					"due_date": due,
					"responsible": obligation.responsible,
					"reviewer": obligation.reviewer,
					"task_key": task_key(template.name, profile.company, registration, period_end),
				}
			)
	return candidates


def obligation_periods(template, obligation, limit: date, agm_dates: dict) -> list[tuple[date, date]]:
	start = getdate(obligation.start_from)
	if template.due_after_event:
		return [
			(getdate(add_days(add_months(year_end, -12), 1)), year_end)
			for year_end in sorted(agm_dates)
			if year_end >= start
		]
	return periods(template.frequency, template.period_basis, start, limit)


def generate_tasks(company: str | None = None, today: date | None = None) -> int:
	today = getdate(today or nowdate())
	filters = {"company": company} if company else {}
	return sum(
		generate_for_profile(name, today)
		for name in frappe.get_all("Company Compliance Profile", filters=filters, pluck="name")
	)


def generate_for_profile(profile_name: str, today: date) -> int:
	profile = frappe.get_doc("Company Compliance Profile", profile_name)
	candidates = candidate_tasks(profile, today)
	if not candidates:
		return 0
	existing = set(
		frappe.get_all(
			"Compliance Task",
			filters={"task_key": ("in", [values["task_key"] for values in candidates])},
			pluck="task_key",
		)
	)
	extensions = extensions_for([values["obligation_template"] for values in candidates])
	made = 0
	for values in candidates:
		if values["task_key"] in existing:
			continue
		extension = find_extension(extensions, values["obligation_template"], values["period_end"])
		if extension:
			values["extended_due_date"] = extension.new_due_date
			values["extension"] = extension.name
		task = frappe.get_doc(values)
		task.flags.ignore_permissions = True  # made by the scheduler or a manager's button
		task.insert()
		made += 1
	return made


def run_daily():
	today = getdate(nowdate())
	for name in frappe.get_all("Company Compliance Profile", pluck="name"):
		run_for_item(name, lambda name=name: generate_for_profile(name, today))
	refresh_overdue(today)
	if not get_settings().enabled:
		return
	send_task_reminders(today)
	send_task_escalations(today)


def refresh_overdue(today: date):
	open_tasks = frappe.get_all(
		"Compliance Task",
		filters={"status": ("not in", CLOSED_TASK_STATUSES)},
		fields=["name", "is_overdue", "effective_due_date"],
	)
	for task in open_tasks:
		overdue = int(getdate(task.effective_due_date) < today)
		if overdue != task.is_overdue:
			run_for_item(task.name, lambda name=task.name: frappe.get_doc("Compliance Task", name).save())


TASK_FIELDS = [
	"name",
	"obligation_template",
	"period_label",
	"company",
	"effective_due_date",
	"responsible",
	"reviewer",
]


def send_task_reminders(today: date):
	tasks = frappe.get_all(
		"Compliance Task",
		filters={"status": ("not in", CLOSED_TASK_STATUSES), "effective_due_date": (">=", today)},
		fields=TASK_FIELDS,
	)
	due = []
	for task in tasks:
		template = frappe.get_cached_doc("Compliance Obligation Template", task.obligation_template)
		days_left = date_diff(task.effective_due_date, today)
		passed = [rule.days_before for rule in template.reminders if rule.days_before >= days_left]
		if passed:
			days = min(passed)
			due.append((task, days, f"{task.name}|reminder|{days}|{task.effective_due_date}"))
	sent = already_sent([key for _task, _days, key in due])
	for task, days, key in due:
		if key not in sent:
			run_for_item(task.name, lambda task=task, days=days, key=key: remind_task(task, days, key))


def remind_task(task, days: int, key: str):
	title = f"{task.obligation_template} ({task.period_label})"
	subject = _("{0} is due on {1}").format(title, formatdate(task.effective_due_date))
	message = _("{0} for {1} is due on {2}.").format(
		escape_html(title), escape_html(task.company), formatdate(task.effective_due_date)
	)
	write_log(
		"Reminder", key, [task.responsible], task=task.name, rule_days=days, due_date=task.effective_due_date
	)
	notify([task.responsible], subject, message, "Compliance Task", task.name)


def send_task_escalations(today: date):
	cut_off = add_days(today, -escalate_after_days())
	tasks = frappe.get_all(
		"Compliance Task",
		filters={"status": ("not in", CLOSED_TASK_STATUSES), "effective_due_date": ("<=", cut_off)},
		fields=TASK_FIELDS,
	)
	due = [(task, f"{task.name}|escalation|{task.effective_due_date}") for task in tasks]
	sent = already_sent([key for _task, key in due])
	managers = compliance_managers()
	looking_after = relationship_managers(task.company for task, _key in due)
	for task, key in due:
		if key not in sent:
			to = [*managers, looking_after.get(task.company)]
			run_for_item(task.name, lambda task=task, key=key, to=to: escalate_task(task, key, to))


def escalate_task(task, key: str, managers: list[str]):
	"""`managers`: the compliance managers, and the client's relationship manager on a firm."""
	recipients = list(dict.fromkeys(user for user in [task.reviewer, *managers] if user))
	title = f"{task.obligation_template} ({task.period_label})"
	subject = _("Overdue filing: {0}").format(title)
	message = _("{0} for {1} was due on {2} and is not filed. It is held by {3}.").format(
		escape_html(title),
		escape_html(task.company),
		formatdate(task.effective_due_date),
		escape_html(task.responsible),
	)
	write_log("Escalation", key, recipients, task=task.name, due_date=task.effective_due_date)
	notify(recipients, subject, message, "Compliance Task", task.name)
