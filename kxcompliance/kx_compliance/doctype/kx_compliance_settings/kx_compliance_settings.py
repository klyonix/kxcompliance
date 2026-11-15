# Copyright (c) 2025, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime


class KXComplianceSettings(Document):
	def validate(self):
		# The installed app's icon is fetched without signing in, so it has to be public.
		if self.app_logo and self.app_logo.startswith("/private/"):
			frappe.throw(_("Attach the App Logo as a public file, so phones can show it."))
		# A changed privacy notice is a new version, which everyone accepts again.
		if self.has_value_changed("privacy_notice") and not self.flags.in_insert:
			self.notice_version = (cint(self.notice_version) or 1) + 1
			self.notice_changed_on = now_datetime()
