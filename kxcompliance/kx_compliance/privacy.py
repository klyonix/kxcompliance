# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""What the app does for the Digital Personal Data Protection Act, 2023 and its Rules of 2025.

The firm or company using the app is the data fiduciary for the personal data in it: its people,
its clients' logins, and signatories' PAN, DIN, mobile and email. The app gives it:

- a privacy notice everyone accepts in the app before using it, again whenever it changes, with
  who accepted which version and when (Privacy Consent), and consent that can be withdrawn;
- requests from a person to see, correct or erase their data, or a grievance (Privacy Request),
  answered by a manager within RESPONSE_DAYS;
- a breach log (Personal Data Breach), with the Board's report due BOARD_HOURS after discovery;
- PAN and mobile numbers masked to all but managers (the Signatory fields' Mask setting);
- the reminder log's addresses erased once they are older than the period set in Settings.
"""

import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.utils import add_days, cint, get_datetime, now_datetime

from kxcompliance.install import CLIENT_ROLE, ROLES

SETTINGS = "KX Compliance Settings"
CONSENT = "Privacy Consent"
REQUEST = "Privacy Request"
REQUEST_TYPES = ("See my data", "Correct my data", "Erase my data", "Grievance")
DETAILS_MAX = 2000
# Days a manager has to answer a request (a grievance, under the DPDP Rules).
RESPONSE_DAYS = 90
# Hours after discovery by which a breach is reported to the Data Protection Board.
BOARD_HOURS = 72
# Logs are kept at least a year (DPDP Rules, reasonable security safeguards).
MIN_LOG_DAYS = 365
MAX_LOG_DAYS = 3650

# The notice used until a manager writes the organisation's own. {fiduciary}, {officer} and
# {email} are filled in when it is shown.
DEFAULT_NOTICE = """<p><strong>{fiduciary}</strong> uses this app to keep its statutory filings,
licences, registrations and legal matters on time. To do that it keeps some personal data about
you, and this notice says what, why, and what you can ask for.</p>
<p><strong>What we keep.</strong> Your name, email address and role in the app, and what you do
in it (the filings, records and documents you add or change). For directors, partners and other
signatories: name, designation, DIN, PAN, email and mobile number. The emails the app sends you,
with when they were sent.</p>
<p><strong>Why.</strong> To let you sign in, to remind you and your team of what falls due, to
file and keep records the law requires, and to keep the app secure. It is not used for
marketing and is not sold.</p>
<p><strong>Who sees it.</strong> The people {fiduciary} gives access to the app, each as their
role allows. PAN and mobile numbers are shown in full to managers only. The data stays on
{fiduciary}'s server and its backups.</p>
<p><strong>How long.</strong> As long as you use the app, and afterwards as long as the law
requires the records to be kept. The addresses on reminder emails are erased after the period
{fiduciary} sets, at least a year.</p>
<p><strong>Your rights.</strong> From Account in the app you can ask to see your data, have it
corrected or erased, raise a grievance, or withdraw this consent. Withdrawing means you can no
longer use the app. A request is answered within {days} days. If you are not satisfied, you
may complain to the Data Protection Board of India.</p>
<p><strong>Grievance officer.</strong> {officer} ({email}).</p>"""

# The same for a firm's client's login, who sees the firm's work for their companies.
CLIENT_NOTICE = """<p><strong>{fiduciary}</strong> uses this app to share with you its work for
your companies: their filings, the documents it needs from you, and its bills. To do that it keeps
some personal data about you, and this notice says what, why, and what you can ask for.</p>
<p><strong>What we keep.</strong> Your name and email address, when you sign in, and the
documents you upload. The emails the app sends you, with when they were sent.</p>
<p><strong>Why.</strong> To let you sign in, to tell you what {fiduciary} needs from you and when,
and to keep the records the law requires. It is not used for marketing and is not sold.</p>
<p><strong>Who sees it.</strong> The people at {fiduciary} who work for your companies, each as
their role allows. The data stays on {fiduciary}'s server and its backups.</p>
<p><strong>How long.</strong> As long as you use the app, and afterwards as long as the law
requires the records to be kept.</p>
<p><strong>Your rights.</strong> From Account in the app you can ask to see your data, have it
corrected or erased, raise a grievance, or withdraw this consent. Withdrawing means you can no
longer sign in. A request is answered within {days} days. If you are not satisfied, you may
complain to the Data Protection Board of India.</p>
<p><strong>Grievance officer.</strong> {officer} ({email}).</p>"""


def settings():
	return frappe.get_cached_doc(SETTINGS)


def fiduciary() -> str:
	"""Whose data it is to protect: the site's default company, else the app's name."""
	return frappe.defaults.get_global_default("company") or settings().app_name or "KlyONIX Compliance"


def current_version() -> int:
	return cint(settings().notice_version) or 1


def is_client_reader(user: str | None = None) -> bool:
	"""Someone at a firm's client, not one of the firm's people."""
	roles = set(frappe.get_roles(user))
	return CLIENT_ROLE in roles and not roles & (set(ROLES) | {"System Manager"})


def standard_notice(for_client: bool = False) -> str:
	"""The app's own notice, with the organisation and its grievance officer filled in; a client's
	login reads the one written for clients."""
	doc = settings()
	name = fiduciary()
	return (CLIENT_NOTICE if for_client else DEFAULT_NOTICE).format(
		fiduciary=frappe.utils.escape_html(name),
		officer=frappe.utils.escape_html(doc.grievance_officer or _("The grievance officer")),
		email=frappe.utils.escape_html(
			doc.grievance_email
			or (
				_("ask {0} for the address").format(name)
				if for_client
				else _("ask your manager for the address")
			)
		),
		days=RESPONSE_DAYS,
	)


def notice() -> dict:
	"""The privacy notice as the person reads it, and whether they have accepted this version."""
	doc = settings()
	return {
		# A firm's own notice is written for its people; its clients read the one for clients.
		"text": standard_notice(for_client=True)
		if is_client_reader()
		else doc.privacy_notice or standard_notice(),
		"version": current_version(),
		"fiduciary": fiduciary(),
		"grievance_officer": doc.grievance_officer or "",
		"grievance_email": doc.grievance_email or "",
		"accepted": not notice_due(),
		"response_days": RESPONSE_DAYS,
	}


def active_consent(user: str | None = None) -> dict | None:
	"""This person's consent to the current notice that they have not withdrawn, if any."""
	consent = frappe.qb.DocType(CONSENT)
	rows = (
		frappe.qb.from_(consent)
		.select(consent.name, consent.accepted_on)
		.where(
			(consent.user == (user or frappe.session.user))
			& (consent.notice_version == current_version())
			& consent.withdrawn_on.isnull()
		)
		.orderby(consent.accepted_on, order=Order.desc)
		.limit(1)
	).run(as_dict=True)
	return rows[0] if rows else None


def notice_due(user: str | None = None) -> bool:
	return active_consent(user) is None


def accept(version: int) -> dict:
	"""This person accepts the notice they were shown, unless it changed while they read it."""
	if cint(version) != current_version():
		frappe.throw(_("The privacy notice has changed since you opened it. Read the new one, then accept."))
	if not notice_due():
		return {"accepted": True}
	consent = frappe.get_doc(
		{
			"doctype": CONSENT,
			"user": frappe.session.user,
			"notice_version": current_version(),
			"accepted_on": now_datetime(),
		}
	)
	# The app's own record of what the person agreed to; nobody else writes it.
	consent.insert(ignore_permissions=True)
	return {"accepted": True}


def withdraw() -> dict:
	"""This person withdraws consent: every consent of theirs still in force is ended now."""
	names = frappe.get_all(
		CONSENT, filters={"user": frappe.session.user, "withdrawn_on": ("is", "not set")}, pluck="name"
	)
	now = now_datetime()
	for name in names:
		consent = frappe.get_doc(CONSENT, name)
		consent.withdrawn_on = now
		# Their own record, which they may end but not edit or read in the Desk.
		consent.save(ignore_permissions=True)
	return {"withdrawn": len(names)}


def raise_request(request_type: str, details: str) -> dict:
	"""Record a request from this person about their own data, for a manager to answer."""
	if request_type not in REQUEST_TYPES:
		frappe.throw(_("{0} is not a kind of privacy request.").format(request_type))
	details = (details or "").strip()
	if not details:
		frappe.throw(_("Say what you are asking for."))
	if len(details) > DETAILS_MAX:
		frappe.throw(_("Keep the details under {0} characters.").format(DETAILS_MAX))
	request = frappe.get_doc(
		{
			"doctype": REQUEST,
			"requested_by": frappe.session.user,
			"request_type": request_type,
			"details": details,
		}
	)
	# Anyone may ask about their own data; only managers read or answer the requests.
	request.insert(ignore_permissions=True)
	return {"name": request.name, "due_by": request.due_by}


def my_requests() -> list[dict]:
	"""This person's own requests and the answers, newest first."""
	# Only rows where they are the requester, so no one else's request is read.
	return frappe.get_all(
		REQUEST,
		filters={"requested_by": frappe.session.user},
		fields=[
			"name",
			"request_type",
			"details",
			"status",
			"received_on",
			"due_by",
			"response",
			"closed_on",
		],
		order_by="received_on desc",
		limit=50,
	)


def log_days() -> int:
	return max(cint(settings().reminder_log_days) or MIN_LOG_DAYS, MIN_LOG_DAYS)


def erase_old_log_addresses() -> None:
	"""Blank the addresses on reminder log entries older than the period kept.

	The entries themselves stay: each one's key stops the same reminder going out twice.
	"""
	cutoff = add_days(now_datetime(), -log_days())
	log = frappe.qb.DocType("Compliance Reminder Log")
	(
		frappe.qb.update(log)
		.set(log.sent_to, "")
		.where((log.sent_on < cutoff) & log.sent_to.isnotnull() & (log.sent_to != ""))
	).run()


def run_daily():
	try:
		erase_old_log_addresses()
	except Exception:
		# A scheduled job: undo the half-done update and record why.
		frappe.db.rollback()
		frappe.log_error(title="Erasing old reminder log addresses failed")


def board_due_by(discovered_on) -> str:
	return frappe.utils.add_to_date(get_datetime(discovered_on), hours=BOARD_HOURS)
