# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

from compliance_plus.compliance_plus.legal import CLOSED_CASE_STATUSES


class LegalCase(Document):
	def validate(self):
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
			self.pass_people_to_open_dates()

	def pass_people_to_open_dates(self):
		# Legal Dates carry the case's people so lists can be filtered by them.
		legal_date = frappe.qb.DocType("Legal Date")
		(
			frappe.qb.update(legal_date)
			.set(legal_date.responsible, self.responsible)
			.set(legal_date.reviewer, self.reviewer)
			.where(
				(legal_date.reference_doctype == self.doctype)
				& (legal_date.reference_name == self.name)
				& (legal_date.status == "Scheduled")
			)
		).run()
