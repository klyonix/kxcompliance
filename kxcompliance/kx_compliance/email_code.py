# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""A one-time code by email, for actions that cannot be undone (RK, 21 Nov 2026): erasing a
person, and deleting an account's data in the hosted service.

The code goes to the signed-in person's own email, so whoever is at the keyboard must also hold
that mailbox. It is good for CODE_MINUTES, for one action on one record, and once; after
MAX_TRIES wrong codes a new one must be sent. Only a hash is kept, in the cache.
"""

import hashlib
import hmac
import secrets

import frappe
from frappe import _
from frappe.utils import cint, escape_html

from kxcompliance import scoped
from kxcompliance.kx_compliance.people import outgoing_email

CODE_MINUTES = 10
MAX_TRIES = 5
DIGITS = 6


def cache_key(purpose: str, key: str) -> str:
	return f"kx_email_code|{frappe.session.user}|{purpose}|{key}"


def digest(code: str, purpose: str, key: str) -> str:
	salt = f"{frappe.session.user}|{purpose}|{key}|{frappe.local.site}"
	return hashlib.sha256(f"{salt}|{code}".encode()).hexdigest()


def send(purpose: str, key: str, what: str) -> dict:
	"""Email a new code to the signed-in person, for `what` (said in the email)."""
	if not outgoing_email():
		frappe.throw(
			_(
				"This needs a code sent by email, and the app cannot send email yet. Set up outgoing email first."
			)
		)
	email = scoped.get_value("User", frappe.session.user, "email") or frappe.session.user
	code = f"{secrets.randbelow(10**DIGITS):0{DIGITS}d}"
	frappe.cache.set_value(
		cache_key(purpose, key),
		{"hash": digest(code, purpose, key), "tries": 0},
		expires_in_sec=CODE_MINUTES * 60,
	)
	subject = _("Your code to confirm: {0}").format(what)
	frappe.sendmail(
		recipients=[email],
		subject=subject,
		message="".join(
			(
				f"<p>{escape_html(_('Your code is'))} <strong>{code}</strong>.</p>",
				f"<p>{escape_html(_('Enter it to confirm: {0}.').format(what))}</p>",
				f"<p>{escape_html(_('It works once, for {0} minutes.').format(CODE_MINUTES))}</p>",
				f"<p>{escape_html(_('If you did not ask for this, someone may be using your login: change your password.'))}</p>",
			)
		),
		now=True,
	)
	return {"sent_to": masked(email), "minutes": CODE_MINUTES}


def check(purpose: str, key: str, code: str | None):
	"""Refuse unless `code` is the one last sent for this action; it is used up when right."""
	name = cache_key(purpose, key)
	stored = frappe.cache.get_value(name)
	if not stored:
		frappe.throw(_("Send yourself a code first; the last one has run out or was used."))
	given = "".join(ch for ch in str(code or "") if ch.isdigit())
	if not hmac.compare_digest(stored["hash"], digest(given, purpose, key)):
		tries = cint(stored.get("tries")) + 1
		if tries >= MAX_TRIES:
			frappe.cache.delete_value(name)
			frappe.throw(_("That code is wrong, {0} times now. Send yourself a new one.").format(tries))
		frappe.cache.set_value(
			name, {"hash": stored["hash"], "tries": tries}, expires_in_sec=CODE_MINUTES * 60
		)
		frappe.throw(_("That code is wrong. Check the email and try again."))
	frappe.cache.delete_value(name)


def masked(email: str) -> str:
	"""ra****@example.com: enough to know which mailbox, not to read it out."""
	local, _sep, domain = email.partition("@")
	return f"{local[:2]}{'*' * max(len(local) - 2, 1)}@{domain}" if domain else email
