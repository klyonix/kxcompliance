# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from kxcompliance import scoped


class CompliancePenaltyFigures(Document):
	def validate(self):
		if not scoped.get_value("Compliance Obligation Template", self.obligation_template, "is_standard"):
			frappe.throw(
				_("{0} is your own obligation; change its figures on the obligation itself.").format(
					self.obligation_template
				)
			)
		if scoped.exists(
			self.doctype, {"obligation_template": self.obligation_template, "name": ("!=", self.name)}
		):
			frappe.throw(_("You already have your own figures for {0}.").format(self.obligation_template))
