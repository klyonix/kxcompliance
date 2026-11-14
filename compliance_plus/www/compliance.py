# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from compliance_plus.api import boot, can_open_app

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/compliance"
		# Temporary, so a browser does not remember it and loop back to login once signed in.
		raise frappe.Redirect(302)
	if not can_open_app():
		frappe.throw(_("You do not have access to the compliance app."), frappe.PermissionError)
	context.boot = boot()
	# A page render is a GET and is not committed for us; the CSRF token above is stored in the session.
	frappe.db.commit()  # nosemgrep
	return context
