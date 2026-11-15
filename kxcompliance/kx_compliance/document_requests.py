# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""A CA/CS firm asks a client for a document, the client uploads it in the app, the firm accepts it.

The client's logins are told by notification and email, and reminded two days before the due
date, on it, and then weekly while it is overdue; the person who asked is told once it is
overdue. Like every reminder, each message is recorded in a Compliance Reminder Log first, whose
unique key keeps a second run from sending it again.
"""

from email.utils import parseaddr

import frappe
from frappe import _
from frappe.utils import date_diff, escape_html, formatdate, get_url, getdate, now_datetime, nowdate

from kxcompliance.kx_compliance.register import get_settings
from kxcompliance.kx_compliance.reminders import (
	already_sent,
	notify,
	run_for_item,
	sender_address,
	write_log,
)

DOCTYPE = "Document Request"
OPEN_STATUSES = ("Requested", "Uploaded")
REMIND_DAYS_BEFORE = (2, 0)
OVERDUE_EVERY_DAYS = 7
REQUEST_FIELDS = ["name", "title", "client", "company", "due_date", "requested_by", "is_overdue"]


def logins_of(clients: list[str]) -> dict[str, list[str]]:
	"""The users of each client's logins that are on."""
	rows = frappe.get_all(
		"Compliance Client Login",
		filters={"parent": ("in", clients or [""]), "parenttype": "Compliance Client", "enabled": 1},
		fields=["parent", "user"],
	)
	result: dict[str, list[str]] = {}
	for row in rows:
		if row.user:
			result.setdefault(row.parent, []).append(row.user)
	return result


def app_link(name: str) -> str:
	return get_url(f"/compliance/requests/{name}")


def message(request, lines: list[str]) -> str:
	"""An email body: the given lines, what is needed, and the link to upload."""
	parts = [f"<p>{line}</p>" for line in lines]
	if request.details:
		parts.append(f"<p>{escape_html(request.details)}</p>")
	link = app_link(request.name)
	parts.append(f'<p><a href="{link}">{escape_html(_("Upload it in the app"))}</a></p>')
	return "".join(parts)


def tell_client(request, subject: str, lines: list[str]) -> bool:
	"""Tell the client's logins about a request, or, for a client with none, email its contact
	(RK, 15 Nov 2026); False when nobody could be told."""
	users = logins_of([request.client]).get(request.client, [])
	if users:
		notify(users, subject, message(request, lines), DOCTYPE, request.name)
		return True
	contact = frappe.db.get_value("Compliance Client", request.client, "contact_email")
	return email_contact(request, contact, subject, lines)


def email_contact(request, address: str | None, subject: str, lines: list[str]) -> bool:
	"""Email a client's contact, who has no login: what is needed, and to reply with the file.

	The email is filed on the request, so the reply comes back to it and its file is taken as the
	upload (take_emailed_file). False when there is no address or the app sends no email."""
	sender = sender_address()
	if not address or not sender:
		return False
	parts = [f"<p>{line}</p>" for line in lines if line]
	if request.details:
		parts.append(f"<p>{escape_html(request.details)}</p>")
	parts.append(
		"<p>"
		+ escape_html(
			_("Reply to this email with the file attached; it reaches {0} directly.").format(firm_name())
		)
		+ "</p>"
	)
	frappe.sendmail(
		recipients=[address],
		sender=sender,
		subject=subject,
		message="".join(parts),
		reference_doctype=DOCTYPE,
		reference_name=request.name,
	)
	return True


def asked(request):
	"""A new request: tell the client, or tell the firm that nobody could be told."""
	subject = _("{0} needs: {1}").format(firm_name(), request.title)
	lines = [
		escape_html(
			_("Please upload {0} for {1} by {2}.").format(
				request.title, request.company, formatdate(request.due_date)
			)
		)
	]
	if not tell_client(request, subject, lines):
		frappe.msgprint(
			_(
				"{0} has no login that is on and no contact email the app can write to, so nobody there was told. Send them the request yourself."
			).format(request.client),
			indicator="orange",
		)


def sent_back(request):
	subject = _("Please send {0} again").format(request.title)
	lines = [
		escape_html(_("{0} could not use what was uploaded for {1}.").format(firm_name(), request.title)),
		escape_html(request.firm_note or ""),
	]
	tell_client(request, subject, lines)


def received(request, document, by: str | None = None):
	"""A document arrived: mark the request uploaded, put the file on its filing, tell the firm.

	`by` names who sent it when it came by email rather than through the app."""
	if request.status == "Requested":
		request.status = "Uploaded"
	request.uploaded_on = now_datetime()
	request.flags.status_change = True
	# A client's login reads the request but may not write it; uploading is what moves it on.
	request.save(ignore_permissions=True)
	if request.compliance_task:
		frappe.get_doc(
			{
				"doctype": "File",
				"file_name": document.file_name,
				"file_url": document.file_url,
				"is_private": document.is_private,
				"attached_to_doctype": "Compliance Task",
				"attached_to_name": request.compliance_task,
			}
		).insert(ignore_permissions=True)  # the same file, also shown on the filing it is for
	if request.requested_by and request.requested_by != frappe.session.user:
		sender = by or frappe.utils.get_fullname(frappe.session.user)
		subject = _("{0} uploaded {1}").format(sender, request.title)
		body = escape_html(
			_("{0} for {1} is ready for you to check: accept it or send it back.").format(
				document.file_name, request.company
			)
		)
		notify([request.requested_by], subject, f"<p>{body}</p>", DOCTYPE, request.name)


def client_addresses(client: str) -> set[str]:
	"""The email addresses a client may answer from: its logins' and its contact's."""
	users = logins_of([client]).get(client, [])
	addresses = set(frappe.get_all("User", filters={"name": ("in", users or [""])}, pluck="email"))
	contact = frappe.db.get_value("Compliance Client", client, "contact_email")
	if contact:
		addresses.add(contact)
	return {address.strip().lower() for address in addresses if address}


def take_emailed_file(file_doc, method=None):
	"""File.after_insert: a client answered a document request by email (RK, 15 Nov 2026).

	Frappe files a reply to a request's email as a Communication on the request, and saves each
	attachment on that Communication. A file from one of the client's own addresses, while the
	request is open, goes on the request as an upload in the app would; anything else stays on the
	reply, and the person who asked is told to look at it.
	"""
	if file_doc.attached_to_doctype != "Communication" or not file_doc.attached_to_name:
		return
	reply = frappe.db.get_value(
		"Communication",
		file_doc.attached_to_name,
		["reference_doctype", "reference_name", "sent_or_received", "sender", "sender_full_name"],
		as_dict=True,
	)
	if not reply or reply.reference_doctype != DOCTYPE or reply.sent_or_received != "Received":
		return
	request = frappe.get_doc(DOCTYPE, reply.reference_name)
	sender = parseaddr(reply.sender or "")[1].strip().lower()
	if request.status in OPEN_STATUSES and sender in client_addresses(request.client):
		document = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": file_doc.file_name,
				"file_url": file_doc.file_url,
				"is_private": 1,
				"attached_to_doctype": DOCTYPE,
				"attached_to_name": request.name,
			}
		)
		# Mail is read by the system, not by a user: the client's own address is the check here.
		document.insert(ignore_permissions=True)
		received(request, document, by=reply.sender_full_name or sender)
		return
	if request.requested_by:
		subject = _("An email about {0} needs a look").format(request.title)
		body = escape_html(
			_(
				"{0} sent {1} by email. It is on the request's activity; it was not taken as the document."
			).format(reply.sender or _("Someone"), file_doc.file_name)
		)
		notify([request.requested_by], subject, f"<p>{body}</p>", DOCTYPE, request.name)


def firm_name() -> str:
	return get_settings().app_name or _("Your firm")


def run_daily():
	today = getdate(nowdate())
	refresh_overdue(today)
	if not get_settings().enabled:
		return
	send_reminders(today)


def refresh_overdue(today):
	rows = frappe.get_all(
		DOCTYPE,
		filters={"status": ("in", OPEN_STATUSES)},
		fields=["name", "status", "due_date", "is_overdue"],
	)
	for row in rows:
		overdue = int(row.status == "Requested" and getdate(row.due_date) < today)
		if overdue != row.is_overdue:
			# Saving recomputes the flag in validate.
			run_for_item(row.name, lambda name=row.name: frappe.get_doc(DOCTYPE, name).save())


def reminder_due(days_left: int) -> bool:
	if days_left in REMIND_DAYS_BEFORE:
		return True
	return days_left < 0 and -days_left % OVERDUE_EVERY_DAYS == 0


def send_reminders(today):
	rows = frappe.get_all(DOCTYPE, filters={"status": "Requested"}, fields=REQUEST_FIELDS)
	planned = []
	for row in rows:
		days_left = date_diff(row.due_date, today)
		if reminder_due(days_left):
			planned.append((row, days_left, f"{DOCTYPE}|{row.name}|{row.due_date}|{days_left}"))
		if days_left == -1:
			planned.append((row, None, f"{DOCTYPE}|{row.name}|{row.due_date}|overdue"))
	sent = already_sent([key for _row, _days, key in planned])
	clients = list({row.client for row, _days, _key in planned})
	logins = logins_of(clients)
	# A client with no login is reminded at its contact email, read once for all of them.
	contacts = dict(
		frappe.get_all(
			"Compliance Client",
			filters={"name": ("in", clients or [""])},
			fields=["name", "contact_email"],
			as_list=True,
		)
	)
	for row, days_left, key in planned:
		if key in sent:
			continue
		if days_left is None:
			run_for_item(row.name, lambda row=row, key=key: tell_requester_overdue(row, key))
		else:
			users = logins.get(row.client, [])
			contact = contacts.get(row.client)
			run_for_item(
				row.name,
				lambda row=row, days=days_left, key=key, users=users, contact=contact: remind(
					row, days, key, users, contact
				),
			)


def remind(request, days_left: int, key: str, users: list[str], contact: str | None = None):
	if not users and not (contact and sender_address()):
		return
	write_log(
		"Document Request",
		key,
		users or [contact],
		document_request=request.name,
		rule_days=days_left,
		due_date=request.due_date,
	)
	if days_left > 0:
		when = _("by {0}").format(formatdate(request.due_date))
	elif days_left == 0:
		when = _("today")
	else:
		when = _("since {0}").format(formatdate(request.due_date))
	subject = _("Reminder: {0} is due {1}").format(request.title, when)
	lines = [escape_html(_("{0} needs {1} for {2}.").format(firm_name(), request.title, request.company))]
	if users:
		notify(users, subject, message(request, lines), DOCTYPE, request.name)
	else:
		email_contact(request, contact, subject, lines)


def tell_requester_overdue(request, key: str):
	if not request.requested_by:
		return
	write_log(
		"Document Request",
		key,
		[request.requested_by],
		document_request=request.name,
		due_date=request.due_date,
	)
	subject = _("{0} has not sent {1}").format(request.client, request.title)
	body = escape_html(
		_("It was due on {0}. The client is reminded weekly until it arrives.").format(
			formatdate(request.due_date)
		)
	)
	notify([request.requested_by], subject, f"<p>{body}</p>", DOCTYPE, request.name)
