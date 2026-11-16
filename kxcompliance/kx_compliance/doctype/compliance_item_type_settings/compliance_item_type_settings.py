# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from kxcompliance import scoped


class ComplianceItemTypeSettings(Document):
	def validate(self):
		if scoped.exists(self.doctype, {"item_type": self.item_type, "name": ("!=", self.name)}):
			frappe.throw(_("You already have your own settings for {0}.").format(self.item_type))
		seen = set()
		for rule in self.reminders:
			if rule.days_before in seen:
				frappe.throw(
					_("Row {0}: a reminder {1} days before expiry is already set.").format(
						rule.idx, rule.days_before
					)
				)
			seen.add(rule.days_before)
