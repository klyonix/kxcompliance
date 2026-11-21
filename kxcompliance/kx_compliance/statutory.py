# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Periods, due dates and task generation for the statutory calendar."""

import calendar
from datetime import date

import frappe
from frappe import _
from frappe.utils import add_days, add_months, date_diff, escape_html, formatdate, getdate, nowdate

from kxcompliance import scoped
from kxcompliance.kx_compliance.doctype.compliance_task.compliance_task import (
	NOT_YET_FILED,
	is_time_barred,
)
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
# How far past either end to look for periods that fall due inside the window though they end outside
# it: no return is due more than a year after its period ends, or before its period begins.
LOOK_BACK_MONTHS = 24
LOOK_AHEAD_MONTHS = 12


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
	return scoped.get_all(
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
		for period_start, period_end, due in obligation_periods(template, obligation, limit, agm_dates):
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


def obligation_periods(template, obligation, limit: date, agm_dates: dict) -> list[tuple[date, date, date]]:
	"""Each period with its due date, from the obligation's start up to the limit.

	A period counts from the start if it ends or falls due on or after it, so a company set up in
	November still gets last year's annual return due that month. It counts up to the limit if it
	ends or falls due by then, so a payment due before its period ends is not made late.
	"""
	start = getdate(obligation.start_from)
	if template.due_after_event:
		return [
			(
				getdate(add_days(add_months(year_end, -12), 1)),
				year_end,
				getdate(add_days(agm_dates[year_end], template.days_after_event)),
			)
			for year_end in sorted(agm_dates)
			if max(year_end, getdate(add_days(agm_dates[year_end], template.days_after_event))) >= start
		]
	found = []
	skipped = template.skipped_months()
	window = periods(
		template.frequency,
		template.period_basis,
		getdate(add_months(start, -LOOK_BACK_MONTHS)),
		getdate(add_months(limit, LOOK_AHEAD_MONTHS)),
	)
	for period_start, period_end in window:
		if period_end.month in skipped:
			continue
		due = due_date(template, period_end)
		if max(period_end, due) >= start and min(period_end, due) <= limit:
			found.append((period_start, period_end, due))
	return found


def generate_tasks(company: str | None = None, today: date | None = None) -> int:
	today = getdate(today or nowdate())
	filters = {"company": company} if company else {}
	return sum(
		generate_for_profile(name, today)
		for name in scoped.get_all("Company Compliance Profile", filters=filters, pluck="name")
	)


def generate_for_profile(profile_name: str, today: date) -> int:
	profile = frappe.get_doc("Company Compliance Profile", profile_name)
	candidates = candidate_tasks(profile, today)
	if not candidates:
		return 0
	existing = set(
		scoped.get_all(
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
	for name in scoped.get_all("Company Compliance Profile", pluck="name"):
		run_for_item(name, lambda name=name: generate_for_profile(name, today))
	refresh_overdue(today)
	if not get_settings().enabled:
		return
	send_task_reminders(today)
	send_task_escalations(today)
	send_time_bar_warnings(today)


def refresh_overdue(today: date):
	"""Save each open filing whose overdue or time-barred flag has changed since yesterday."""
	open_tasks = scoped.get_all(
		"Compliance Task",
		filters={"status": ("not in", CLOSED_TASK_STATUSES)},
		fields=[
			"name",
			"status",
			"is_overdue",
			"effective_due_date",
			"is_time_barred",
			"last_filing_date",
			"filed_on",
		],
	)
	for task in open_tasks:
		overdue = int(getdate(task.effective_due_date) < today)
		barred = int(is_time_barred(task.last_filing_date, task.status, task.filed_on, today))
		if overdue != task.is_overdue or barred != task.is_time_barred:
			run_for_item(task.name, lambda name=task.name: frappe.get_doc("Compliance Task", name).save())


TASK_FIELDS = [
	"name",
	"obligation_template",
	"period_label",
	"company",
	"effective_due_date",
	"last_filing_date",
	"responsible",
	"reviewer",
]
# How long before a return's last day to file the managers are warned (RK, 21 Nov 2026).
TIME_BAR_WARNING_DAYS = 90


def send_task_reminders(today: date):
	tasks = scoped.get_all(
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
	tasks = scoped.get_all(
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


def send_time_bar_warnings(today: date):
	"""Warn once, from 90 days before, that a return still to file will soon no longer be accepted."""
	tasks = scoped.get_all(
		"Compliance Task",
		filters={
			# Sent for review means filed on the portal, so only those still to file are warned about.
			"status": ("in", NOT_YET_FILED),
			"last_filing_date": ("between", [today, add_days(today, TIME_BAR_WARNING_DAYS)]),
		},
		fields=TASK_FIELDS,
	)
	due = [(task, f"{task.name}|time-bar|{task.last_filing_date}") for task in tasks]
	sent = already_sent([key for _task, key in due])
	managers = compliance_managers()
	looking_after = relationship_managers(task.company for task, _key in due)
	for task, key in due:
		if key not in sent:
			to = [task.responsible, *managers, looking_after.get(task.company)]
			run_for_item(task.name, lambda task=task, key=key, to=to: warn_time_bar(task, key, to))


def warn_time_bar(task, key: str, people: list[str]):
	"""`people`: who prepares it, the compliance managers, and the client's relationship manager."""
	recipients = list(dict.fromkeys(user for user in [task.reviewer, *people] if user))
	title = f"{task.obligation_template} ({task.period_label})"
	subject = _("Last day to file {0}: {1}").format(title, formatdate(task.last_filing_date))
	message = _(
		"{0} for {1} was due on {2} and is not filed. The portal accepts it only until {3}; after "
		"that it can no longer be filed."
	).format(
		escape_html(title),
		escape_html(task.company),
		formatdate(task.effective_due_date),
		formatdate(task.last_filing_date),
	)
	write_log("Escalation", key, recipients, task=task.name, due_date=task.last_filing_date)
	notify(recipients, subject, message, "Compliance Task", task.name)
