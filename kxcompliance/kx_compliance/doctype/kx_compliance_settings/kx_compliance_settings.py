# Copyright (c) 2025, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class KXComplianceSettings(Document):
	def validate(self):
		# The installed app's icon is fetched without signing in, so it has to be public.
		if self.app_logo and self.app_logo.startswith("/private/"):
			frappe.throw(_("Attach the App Logo as a public file, so phones can show it."))
