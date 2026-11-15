# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from kxcompliance.kx_compliance.legal import (
	CLOSED_CASE_STATUSES,
	cancel_scheduled_dates,
	check_status_change,
	pass_company_to_dates,
	pass_people_to_dates,
)
from kxcompliance.kx_compliance.register import check_reassignment


class LegalCase(Document):
	def validate(self):
		check_reassignment(self)
		check_status_change(self)
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
		if self.status in CLOSED_CASE_STATUSES and self.has_value_changed("status"):
			cancel_scheduled_dates(
				self.doctype, self.name, _("Cancelled: the case was closed as {0}.").format(_(self.status))
			)

	@frappe.whitelist(methods=["POST"])
	def change_status(self, status: str, outcome: str | None = None, closed_on: str | None = None):
		"""Move the case on: stayed, reserved for order, closed with its outcome, or reopened."""
		self.check_permission("write")
		if status not in self.meta.get_field("status").options.split("\n"):
			frappe.throw(_("{0} is not a status a case can have.").format(status))
		if status == self.status:
			frappe.throw(_("{0} is already {1}.").format(self.name, _(status)))
		self.status = status
		if status in CLOSED_CASE_STATUSES:
			if closed_on and getdate(closed_on) > getdate(nowdate()):
				frappe.throw(
					_("Closed On ({0}) cannot be in the future.").format(frappe.format(closed_on, "Date"))
				)
			self.closed_on = closed_on or nowdate()
			if (outcome or "").strip():
				self.outcome = outcome.strip()
		self.save()
