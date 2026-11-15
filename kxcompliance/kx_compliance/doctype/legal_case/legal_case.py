# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

from kxcompliance.kx_compliance.legal import CLOSED_CASE_STATUSES, pass_company_to_dates, pass_people_to_dates
from kxcompliance.kx_compliance.register import check_reassignment


class LegalCase(Document):
	def validate(self):
		check_reassignment(self)
		if self.appeal_of and self.appeal_of == self.name:
			frappe.throw(_("A case cannot be an appeal of itself."))
		if self.amount_involved and not self.risk:
			frappe.throw(
				_("Set the Risk of {0}, because it has an amount involved.").format(self.name or self.title)
			)
		if self.status in CLOSED_CASE_STATUSES:
			self.closed_on = self.closed_on or nowdate()
		else:
			self.closed_on = None

	def on_update(self):
		if self.has_value_changed("responsible") or self.has_value_changed("reviewer"):
			pass_people_to_dates(self.doctype, self.name, self.responsible, self.reviewer)
		if self.has_value_changed("company"):
			pass_company_to_dates(self.doctype, self.name, self.company)
