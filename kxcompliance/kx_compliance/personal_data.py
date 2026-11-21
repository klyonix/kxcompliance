# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""A person's own data under the DPDP Act (RK, 21 Nov 2026).

- See: anyone signed in reads what the app holds about them, any time, and downloads it; the
  grievance officer sees the same for a "See my data" request.
- Erase: for an "Erase my data" request, the grievance officer hands the person's open work to
  someone on the team, then the app removes what identifies them. Records the law requires keep
  the fact, without the person: their login is switched off and renamed "Erased person 7F3A" with
  an address that receives no mail, so filings still show the work was done, by that name. A
  signatory keeps name, designation and DIN, which past filings refer to; PAN, email and mobile
  go, and they are marked inactive. The request records what was done.
"""

import json

import frappe
from frappe import _
from frappe.model.rename_doc import rename_doc
from frappe.sessions import clear_sessions
from frappe.utils import escape_html, now_datetime
from pypika.functions import Replace

from kxcompliance import scoped
from kxcompliance.install import CLIENT_ROLE, ROLES
from kxcompliance.kx_compliance.onboarding import firm_people
from kxcompliance.kx_compliance.people import PROTECTED

REQUEST = "Privacy Request"
ERASE = "Erase my data"
SEE = "See my data"
ERASED_DOMAIN = "erased.invalid"
# The records that name a person, by the field that does: what they hold or review.
NAMED_IN = (
	("Filings", "Compliance Task", ("responsible", "reviewer", "filed_by")),
	("Register items", "Compliance Item", ("responsible", "reviewer")),
	("Legal cases", "Legal Case", ("responsible", "reviewer")),
	("Hearings and deadlines", "Legal Date", ("responsible", "reviewer")),
	("Trademarks", "Trademark", ("responsible", "reviewer")),
	("Document requests", "Document Request", ("requested_by",)),
)
USER_FIELDS = (
	"first_name",
	"middle_name",
	"last_name",
	"mobile_no",
	"phone",
	"birth_date",
	"gender",
	"bio",
	"location",
	"user_image",
)


# --- See ---------------------------------------------------------------------------------------


def summary(user: str) -> dict:
	"""What the app holds about one person: their login, consents, requests, the records naming
	them, their signatory details, the emails sent to them and their sign-ins."""
	person = scoped.get_value(
		"User",
		user,
		["name", "full_name", "email", "mobile_no", "enabled", "creation", "last_login", "user_image"],
		as_dict=True,
	)
	if not person:
		frappe.throw(_("There is no person {0} here.").format(user))
	roles = scoped.get_all("Has Role", filters={"parent": user, "parenttype": "User"}, pluck="role")
	email = person.email or user
	return {
		"made_on": str(now_datetime()),
		"person": {
			"name": person.full_name,
			"email": email,
			"mobile": person.mobile_no or "",
			"signs_in": bool(person.enabled),
			"since": str(person.creation),
			"last_sign_in": str(person.last_login or ""),
			"has_photo": bool(person.user_image),
			"roles": sorted(role for role in roles if role in (*ROLES, CLIENT_ROLE)),
		},
		"consents": scoped.get_all(
			"Privacy Consent",
			filters={"user": user},
			fields=["notice_version", "accepted_on", "withdrawn_on"],
			order_by="accepted_on desc",
		),
		"requests": scoped.get_all(
			REQUEST,
			filters={"requested_by": user},
			fields=["name", "request_type", "status", "received_on", "closed_on"],
			order_by="received_on desc",
		),
		"records": named_in(user),
		"signatory": scoped.get_all(
			"Signatory",
			filters={"email": email},
			fields=["full_name", "designation", "company", "din", "pan", "email", "mobile", "is_active"],
		),
		"client_logins": scoped.get_all(
			"Compliance Client Login", filters={"user": user}, fields=["parent as client", "enabled"]
		),
		"emails_sent": scoped.count("Compliance Reminder Log", {"sent_to": ("like", f"%{email}%")}),
		"sign_ins": scoped.count("Activity Log", {"user": user, "operation": "Login"}),
	}


def named_in(user: str) -> list[dict]:
	"""How many records of each kind name the person. A fixed handful of counts, one per field."""
	rows = []
	for label, doctype, fields in NAMED_IN:
		meta = frappe.get_meta(doctype)
		count = sum(scoped.count(doctype, {field: user}) for field in fields if meta.has_field(field))
		if count:
			rows.append({"label": label, "doctype": doctype, "count": count})
	return rows


def request_of(name: str):
	if not isinstance(name, str) or not scoped.exists(REQUEST, name):
		frappe.throw(_("There is no privacy request {0}.").format(name))
	request = frappe.get_doc(REQUEST, name)
	request.check_permission("write")
	return request


def summary_for_request(name: str) -> dict:
	"""For the grievance officer answering a "See my data" request."""
	request = request_of(name)
	if request.request_type != SEE:
		frappe.throw(_("Request {0} is {1}, not {2}.").format(name, _(request.request_type), _(SEE)))
	return summary(request.requested_by)


# --- Erase -------------------------------------------------------------------------------------


def start_erasing(name: str, hand_to: str, confirm: str) -> dict:
	"""The grievance officer erases the person who asked, in the background."""
	request = request_of(name)
	person = request.requested_by
	if request.request_type != ERASE:
		frappe.throw(_("Request {0} is {1}, not {2}.").format(name, _(request.request_type), _(ERASE)))
	if request.status in ("Done", "Declined") or request.erased_on:
		frappe.throw(_("Request {0} is already {1}.").format(name, _(request.status).lower()))
	if person in PROTECTED or person == frappe.session.user:
		frappe.throw(_("Another manager erases your own data."))
	if (confirm or "").strip().casefold() != person.casefold():
		frappe.throw(_("Type {0} exactly to confirm.").format(person))
	team = {row.name for row in firm_people()}
	if hand_to == person or hand_to not in team:
		frappe.throw(_("Choose someone on the team, other than {0}, to take their open work.").format(person))
	request.status = "In Progress"
	request.save()
	frappe.enqueue(
		"kxcompliance.kx_compliance.personal_data.erase",
		queue="long",
		enqueue_after_commit=True,
		request=name,
		hand_to=hand_to,
		by=frappe.session.user,
	)
	return {"started": True}


def erase(request: str, hand_to: str, by: str):
	"""Background job: hand over the work, answer the person while their address still works,
	then remove what identifies them."""
	from kxcompliance.kx_compliance.handover import run as hand_over

	# The job acts as the manager who started it, so their permissions apply to what it changes.
	frappe.set_user(by)  # nosemgrep
	doc = frappe.get_doc(REQUEST, request)
	if doc.erased_on:
		return  # already done: a job queued twice must not erase the renamed login again
	person = doc.requested_by
	email = scoped.get_value("User", person, "email") or person
	try:
		hand_over(person, hand_to, by)
		done = {"signatories": erase_signatories(email), "reminder_addresses": erase_log_addresses(email)}
		anonymise = scoped.may_anonymise_login(person)
		new_name = f"erased-{frappe.generate_hash(length=8)}@{ERASED_DOMAIN}"
		label = _("Erased person {0}").format(new_name[7:11].upper())
		doc.reload()
		doc.status = "Done"
		doc.response = answer(doc.response, anonymise, done)
		doc.erased_on = now_datetime()
		doc.erasure_record = json.dumps(done | {"login_anonymised": anonymise}, sort_keys=True)
		# Saved before the login changes, so the answer reaches the address they asked from.
		doc.save()
		if anonymise:
			# Renaming a login renames Frappe's own records of it (notification settings and the
			# like), which only Administrator may; the request and the manager were checked above.
			frappe.set_user("Administrator")  # nosemgrep
			anonymise_login(person, new_name, label)
			frappe.set_user(by)  # nosemgrep
		# A job may commit what it finished; nothing above is left half done.
		frappe.db.commit()  # nosemgrep
	except Exception:
		# A background job: undo what was half done, record why, and tell the manager.
		frappe.db.rollback()
		frappe.log_error(title=f"Erasing the person of privacy request {request} failed")
		tell_failed(by, request)


def erase_signatories(email: str) -> int:
	names = scoped.get_all("Signatory", filters={"email": email}, pluck="name")
	for name in names:
		signatory = frappe.get_doc("Signatory", name)
		signatory.pan = None
		signatory.email = None
		signatory.mobile = None
		signatory.is_active = 0
		signatory.save()
	return len(names)


def erase_log_addresses(email: str) -> int:
	log = frappe.qb.DocType("Compliance Reminder Log")
	condition = log.sent_to.like(f"%{email}%") & scoped.where(log)
	count = frappe.qb.from_(log).select(log.name).where(condition).run(pluck=True)
	if count:
		frappe.qb.update(log).set(log.sent_to, "").where(condition).run()
	return len(count)


def anonymise_login(user: str, new_name: str, label: str):
	doc = frappe.get_doc("User", user)
	old_email, old_full_name = doc.email or user, doc.full_name
	for field in USER_FIELDS:
		doc.set(field, None)
	doc.first_name = label
	doc.enabled = 0
	doc.save(ignore_permissions=True)  # the person's own login, erased on their request
	clear_sessions(user, force=True)
	for name in scoped.get_all(
		"File", filters={"attached_to_doctype": "User", "attached_to_name": user}, pluck="name"
	):
		frappe.delete_doc("File", name, ignore_permissions=True)  # their photo, erased with them
	rename_doc(doctype="User", old=user, new=new_name, force=True, ignore_permissions=True, show_alert=False)
	renamed = frappe.get_doc("User", new_name)
	renamed.email = new_name
	renamed.save(ignore_permissions=True)  # the erased login's address, which receives no mail
	member = frappe.qb.DocType("Compliance Client Member")
	frappe.qb.update(member).set(member.full_name, label).where(member.user == new_name).where(
		scoped.where(member)
	).run()
	login = frappe.qb.DocType("Compliance Client Login")
	(
		frappe.qb.update(login)
		.set(login.full_name, label)
		.set(login.email, new_name)
		.set(login.enabled, 0)
		.where(login.user == new_name)
		.where(scoped.where(login))
	).run()
	request = frappe.qb.DocType(REQUEST)
	frappe.qb.update(request).set(request.requester_name, label).where(
		request.requested_by == new_name
	).where(scoped.where(request)).run()
	scrub_traces(old_email, old_full_name, new_name, label)


def scrub_traces(old_email: str, old_full_name: str | None, new_name: str, label: str):
	"""Frappe keeps a person's email and name as text in change history, comments and its sign-in
	log, which renaming the login does not reach: the login's own history goes, and elsewhere the
	old email and name become the erased ones."""
	version = frappe.qb.DocType("Version")
	frappe.qb.from_(version).delete().where(
		(version.ref_doctype == "User") & version.docname.isin([old_email, new_name])
	).where(scoped.where(version)).run()
	requests = frappe.qb.DocType(REQUEST)
	their_requests = (
		frappe.qb.from_(requests)
		.select(requests.name)
		.where(requests.requested_by == new_name)
		.where(scoped.where(requests))
	)
	mentioning = version.data.like(f"%{old_email}%") | (
		(version.ref_doctype == REQUEST) & version.docname.isin(their_requests)
	)
	replaced = Replace(version.data, old_email, new_name)
	if old_full_name:
		replaced = Replace(replaced, old_full_name, label)
	frappe.qb.update(version).set(version.data, replaced).where(mentioning).where(scoped.where(version)).run()
	comment = frappe.qb.DocType("Comment")
	(
		frappe.qb.update(comment)
		.set(comment.comment_email, new_name)
		.set(comment.comment_by, label)
		.where((comment.comment_email == old_email) | (comment.owner == new_name))
		.where(scoped.where(comment))
	).run()
	activity = frappe.qb.DocType("Activity Log")
	frappe.qb.update(activity).set(activity.full_name, label).where(activity.user == new_name).where(
		scoped.where(activity)
	).run()
	communication = frappe.qb.DocType("Communication")
	for field in ("sender", "recipients", "cc", "bcc"):
		frappe.qb.update(communication).set(
			communication[field], Replace(communication[field], old_email, new_name)
		).where(communication[field].like(f"%{old_email}%")).where(scoped.where(communication)).run()


def answer(response: str | None, anonymised: bool, done: dict) -> str:
	lines = [(response or "").strip()] if (response or "").strip() else []
	lines.append(_("Your data has been erased."))
	if anonymised:
		lines.append(_("Your login is switched off, and your name, mobile number and photo are removed."))
	else:
		lines.append(_("Your access to this organisation is removed."))
	if done["signatories"]:
		lines.append(
			_(
				"As a signatory, your PAN, email and mobile are removed; your name, designation and DIN stay, as past filings refer to them."
			)
		)
	lines.append(
		_(
			"Filings and other records the law requires are kept, without your name: the work they record stays, as done by an erased person."
		)
	)
	return "\n\n".join(lines)


def tell_failed(by: str, request: str):
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	enqueue_create_notification(
		by,
		{
			"type": "Alert",
			"document_type": REQUEST,
			"document_name": request,
			"subject": _(
				"Erasing the person of request {0} did not finish; their open work may already have moved. Erase again to finish."
			).format(escape_html(request)),
		},
	)
