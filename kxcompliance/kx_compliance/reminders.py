# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""The daily job: keep statuses current, then remind, escalate and summarise.

Each item is handled inside its own savepoint, so one bad record is logged and
skipped without undoing the others. Every message sent is recorded in a
Compliance Reminder Log before it goes out. Its key is unique, so a second run, or two
runs at once, fail on the log and send nothing.
"""

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
from frappe.utils import (
	add_days,
	date_diff,
	escape_html,
	formatdate,
	getdate,
	now_datetime,
	nowdate,
)

from kxcompliance.kx_compliance.app_links import app_url
from kxcompliance.kx_compliance.register import (
	CLOSED_TASK_STATUSES,
	compute_status,
	due_soon_days,
	escalate_after_days,
	get_settings,
	get_type_rules,
	open_renewal_statuses,
)

QUIET_STATUSES = ("Cancelled", "Renewal in Progress")
OVERDUE_STATUSES = ("Expired", "Lapsed")
ITEM_FIELDS = [
	"name",
	"title",
	"status",
	"item_type",
	"valid_until",
	"certificate",
	"is_cancelled",
	"responsible",
	"reviewer",
	"holder_type",
	"holder",
]
PARTY_EMAIL_FIELDS = {"Customer": "email_id", "Supplier": "email_id"}


def run_daily():
	today = getdate(nowdate())
	refresh_statuses(today)
	if not get_settings().enabled:
		return
	send_reminders(today)
	send_party_reminders(today)
	send_escalations(today)
	if today.strftime("%A") == (get_settings().digest_day or "Monday"):
		send_digests(today)


def refresh_statuses(today):
	items = frappe.get_all("Compliance Item", filters={"is_cancelled": 0}, fields=ITEM_FIELDS)
	rules = get_type_rules([item.item_type for item in items])
	renewals = open_renewal_statuses([item.name for item in items])
	soon = due_soon_days()

	for item in items:
		type_rules = rules.get(item.item_type) or frappe._dict()
		status = compute_status(
			is_cancelled=False,
			valid_until=item.valid_until,
			renewal_status=renewals.get(item.name),
			grace_days=type_rules.grace_days or 0,
			today=today,
			soon_days=soon,
		)
		if status != item.status:
			run_for_item(item.name, lambda name=item.name: frappe.get_doc("Compliance Item", name).save())


def send_reminders(today):
	items = frappe.get_all(
		"Compliance Item",
		filters={"status": ("not in", QUIET_STATUSES), "valid_until": (">=", today)},
		fields=ITEM_FIELDS,
	)
	rules = reminder_days_by_item([item.name for item in items])
	due = []
	for item in items:
		days_left = date_diff(item.valid_until, today)
		passed = [days for days in rules.get(item.name, []) if days >= days_left]
		if passed:
			days = min(passed)
			due.append((item, days, f"{item.name}|reminder|{days}|{item.valid_until}"))

	sent = already_sent([key for _item, _days, key in due])
	for item, days, key in due:
		if key in sent:
			continue
		run_for_item(item.name, lambda item=item, days=days, key=key: remind(item, days, key))


def remind(item, days: int, key: str):
	subject = _("{0} expires on {1}").format(item.title, formatdate(item.valid_until))
	message = _("{0} ({1}) expires on {2}, in {3} days. Start its renewal.").format(
		escape_html(item.title),
		item.name,
		formatdate(item.valid_until),
		date_diff(item.valid_until, nowdate()),
	)
	write_log("Reminder", key, [item.responsible], item=item.name, rule_days=days, due_date=item.valid_until)
	notify([item.responsible], subject, message, "Compliance Item", item.name)


def send_party_reminders(today):
	"""Email a customer or supplier before a licence they hold expires, from the template in Settings."""
	template_name = get_settings().party_email_template
	if not template_name or not get_settings().email_account:
		return
	items = frappe.get_all(
		"Compliance Item",
		filters={
			"holder_type": ("in", list(PARTY_EMAIL_FIELDS)),
			"status": ("not in", QUIET_STATUSES),
			"valid_until": (">=", today),
		},
		fields=ITEM_FIELDS,
	)
	rules = reminder_days_by_item([item.name for item in items])
	due = []
	for item in items:
		days_left = date_diff(item.valid_until, today)
		passed = [days for days in rules.get(item.name, []) if days >= days_left]
		if passed:
			days = min(passed)
			due.append((item, days, f"{item.name}|party|{days}|{item.valid_until}"))
	sent = already_sent([key for _item, _days, key in due])
	template = frappe.get_doc("Email Template", template_name)
	for item, days, key in due:
		if key not in sent:
			run_for_item(
				item.name, lambda item=item, days=days, key=key: remind_party(item, days, key, template)
			)


def remind_party(item, days: int, key: str, template):
	email = frappe.db.get_value(item.holder_type, item.holder, PARTY_EMAIL_FIELDS[item.holder_type])
	if not email:
		return
	context = {
		"doc": item,
		"party": item.holder,
		"party_name": frappe.db.get_value(
			item.holder_type, item.holder, frappe.scrub(item.holder_type) + "_name"
		),
		"valid_until": formatdate(item.valid_until),
		"days_left": date_diff(item.valid_until, nowdate()),
	}
	# Only a System Manager can write an Email Template, and Frappe renders it in its sandboxed Jinja,
	# as it does its own notification templates.
	subject = frappe.render_template(template.subject, context)
	message = frappe.render_template(
		template.response_html if template.use_html else template.response, context
	)
	write_log("Party Reminder", key, [email], item=item.name, rule_days=days, due_date=item.valid_until)
	sender = frappe.db.get_value("Email Account", get_settings().email_account, "email_id")
	frappe.sendmail(
		recipients=[email],
		sender=sender,
		subject=subject,
		message=message,
		reference_doctype="Compliance Item",
		reference_name=item.name,
	)


def send_escalations(today):
	cut_off = add_days(today, -escalate_after_days())
	items = frappe.get_all(
		"Compliance Item",
		filters={"status": ("in", OVERDUE_STATUSES), "valid_until": ("<=", cut_off)},
		fields=ITEM_FIELDS,
	)
	due = [(item, f"{item.name}|escalation|{item.valid_until}") for item in items]
	sent = already_sent([key for _item, key in due])
	managers = compliance_managers()
	for item, key in due:
		if key in sent:
			continue
		run_for_item(item.name, lambda item=item, key=key: escalate(item, key, managers))


def escalate(item, key: str, managers: list[str]):
	recipients = [user for user in [item.reviewer, *managers] if user]
	subject = _("Overdue: {0} expired on {1}").format(item.title, formatdate(item.valid_until))
	message = _("{0} ({1}) expired on {2} and has not been renewed. It is held by {3}.").format(
		escape_html(item.title), item.name, formatdate(item.valid_until), escape_html(item.responsible)
	)
	write_log("Escalation", key, recipients, item=item.name, due_date=item.valid_until)
	notify(recipients, subject, message, "Compliance Item", item.name)


def send_digests(today):
	horizon = add_days(today, due_soon_days())
	items = frappe.get_all(
		"Compliance Item",
		filters={"status": ("!=", "Cancelled"), "valid_until": ("<=", horizon)},
		fields=ITEM_FIELDS,
		order_by="valid_until asc",
	)
	tasks = frappe.get_all(
		"Compliance Task",
		filters={"status": ("not in", CLOSED_TASK_STATUSES), "effective_due_date": ("<=", horizon)},
		fields=[
			"name",
			"obligation_template",
			"period_label",
			"status",
			"effective_due_date",
			"responsible",
			"reviewer",
		],
		order_by="effective_due_date asc",
	)
	by_user: dict[str, list] = {}
	for item in items:
		row = digest_row("Compliance Item", item.name, item.title, item.status, item.valid_until)
		for user in {item.responsible, item.reviewer} - {None, ""}:
			by_user.setdefault(user, []).append(row)
	for task in tasks:
		title = f"{task.obligation_template} ({task.period_label})"
		row = digest_row("Compliance Task", task.name, title, task.status, task.effective_due_date)
		for user in {task.responsible, task.reviewer} - {None, ""}:
			by_user.setdefault(user, []).append(row)
	legal_dates = frappe.get_all(
		"Legal Date",
		filters={"status": "Scheduled", "date": ("<=", horizon)},
		fields=["name", "kind", "reference_title", "status", "date", "is_overdue", "responsible", "reviewer"],
		order_by="date asc",
	)
	for legal_date in legal_dates:
		title = f"{_(legal_date.kind)}: {legal_date.reference_title}"
		status = "Outcome Not Recorded" if legal_date.is_overdue else legal_date.status
		row = digest_row("Legal Date", legal_date.name, title, status, legal_date.date)
		for user in {legal_date.responsible, legal_date.reviewer} - {None, ""}:
			by_user.setdefault(user, []).append(row)

	keys = {user: f"digest|{user}|{today}" for user in by_user}
	sent = already_sent(list(keys.values()))
	for user, user_items in by_user.items():
		if keys[user] in sent:
			continue
		run_for_item(user, lambda user=user, user_items=user_items: digest(user, user_items, keys[user]))


def digest_row(doctype: str, name: str, title: str, status: str, date) -> str:
	return "<tr><td><a href='{url}'>{title}</a></td><td>{status}</td><td>{date}</td></tr>".format(
		url=app_url(doctype, name),
		title=escape_html(title),
		status=escape_html(_(status)),
		date=formatdate(date),
	)


def digest(user: str, rows: list[str], key: str):
	message = "<p>{}</p><table><tr><th>{}</th><th>{}</th><th>{}</th></tr>{}</table>".format(
		_("These compliance items and filings need attention."),
		_("Item"),
		_("Status"),
		_("Date"),
		"".join(rows),
	)
	write_log("Digest", key, [user])
	send_email([user], _("Compliance items needing attention: {0}").format(len(rows)), message)


def run_for_item(label: str, work):
	savepoint = "compliance_item_job"
	frappe.db.savepoint(savepoint)
	try:
		work()
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		frappe.log_error(title=_("Compliance reminder job failed for {0}").format(label))


def reminder_days_by_item(items: list[str]) -> dict[str, list[int]]:
	if not items:
		return {}
	rows = frappe.get_all(
		"Compliance Reminder Rule",
		filters={"parenttype": "Compliance Item", "parent": ("in", items)},
		fields=["parent", "days_before"],
	)
	result: dict[str, list[int]] = {}
	for row in rows:
		result.setdefault(row.parent, []).append(row.days_before)
	return result


def already_sent(keys: list[str]) -> set[str]:
	if not keys:
		return set()
	return set(frappe.get_all("Compliance Reminder Log", filters={"log_key": ("in", keys)}, pluck="log_key"))


def compliance_managers() -> list[str]:
	has_role = frappe.qb.DocType("Has Role")
	user = frappe.qb.DocType("User")
	return (
		frappe.qb.from_(has_role)
		.join(user)
		.on(user.name == has_role.parent)
		.select(user.name)
		.distinct()
		.where(
			(has_role.parenttype == "User")
			& (has_role.role == "Compliance Manager")
			& (user.enabled == 1)
			& (user.user_type == "System User")
		)
	).run(pluck=True)


def notify(users: list[str], subject: str, message: str, doctype: str, name: str):
	users = list(dict.fromkeys(user for user in users if user))
	if not users:
		return
	enqueue_create_notification(
		users,
		{
			"type": "Alert",
			"subject": escape_html(subject),
			"email_content": message,
			"document_type": doctype,
			"document_name": name,
			"from_user": "Administrator",
		},
	)
	send_email(users, subject, message, doctype, name)


def sender_address() -> str | None:
	"""The address the app sends from: the email account chosen in its settings, if any."""
	account = get_settings().email_account
	return frappe.db.get_value("Email Account", account, "email_id") if account else None


def send_email(
	users: list[str], subject: str, message: str, doctype: str | None = None, name: str | None = None
):
	sender = sender_address()
	recipients = frappe.get_all("User", filters={"name": ("in", users), "enabled": 1}, pluck="email")
	if not sender or not recipients:
		return
	frappe.sendmail(
		recipients=recipients,
		sender=sender,
		subject=subject,
		message=message,
		reference_doctype=doctype,
		reference_name=name,
	)


def write_log(
	kind: str,
	key: str,
	recipients: list[str],
	*,
	item: str | None = None,
	task: str | None = None,
	legal_date: str | None = None,
	rule_days: int | None = None,
	due_date=None,
	document_request: str | None = None,
):
	frappe.get_doc(
		{
			"doctype": "Compliance Reminder Log",
			"compliance_item": item,
			"compliance_task": task,
			"legal_date": legal_date,
			"document_request": document_request,
			"kind": kind,
			"rule_days": rule_days,
			"due_date": due_date,
			"sent_to": "\n".join(recipients),
			"sent_on": now_datetime(),
			"log_key": key,
		}
	).insert(ignore_permissions=True)  # written by the scheduler, not by a person
