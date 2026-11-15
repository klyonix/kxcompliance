# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from kxcompliance.kx_compliance.register import CLOSED_TASK_STATUSES, check_reassignment, is_approver

FILED_STATUSES = ("Filed", "Filed Late")
# Set when the task is made or by an extension; nobody edits them by hand.
SCHEDULE_FIELDS = (
	"obligation_template",
	"company",
	"registration_number",
	"period_start",
	"period_end",
	"due_date",
	"extended_due_date",
	"extension",
	"task_key",
	"company_event",
	"reviewed_by",
)


class ComplianceTask(Document):
	def validate(self):
		check_reassignment(self)
		self.effective_due_date = self.extended_due_date or self.due_date
		before = self.get_doc_before_save()
		previous = before.status if before else None
		if before:
			self.protect_schedule(before)
		if self.status != previous:
			self.validate_transition(previous)
		self.is_overdue = int(
			self.status not in CLOSED_TASK_STATUSES and getdate(self.effective_due_date) < getdate(nowdate())
		)

	def protect_schedule(self, before):
		if self.flags.ignore_permissions or is_approver():
			return
		for fieldname in SCHEDULE_FIELDS:
			if str(self.get(fieldname) or "") != str(before.get(fieldname) or ""):
				frappe.throw(
					_("{0} cannot be changed on {1}; only a Compliance Manager can.").format(
						_(self.meta.get_label(fieldname)), self.name
					),
					frappe.PermissionError,
				)

	def validate_transition(self, previous: str | None):
		if previous in CLOSED_TASK_STATUSES and not is_approver():
			frappe.throw(
				_("{0} is {1}; only a Compliance Manager can change it to {2}.").format(
					self.name, _(previous), _(self.status)
				),
				frappe.PermissionError,
			)
		rules = frappe.get_cached_doc("Compliance Obligation Template", self.obligation_template)
		if self.status in ("Ready for Review", *FILED_STATUSES):
			self.validate_filing_details(rules)
		if self.status in FILED_STATUSES:
			self.mark_filed(rules)
		if self.status == "Not Applicable" and not (self.remarks or "").strip():
			frappe.throw(_("Say in Remarks why {0} does not apply.").format(self.name))
		if self.status == "Cancelled" and not is_approver():
			frappe.throw(
				_("Only a Compliance Manager can cancel {0}.").format(self.name), frappe.PermissionError
			)

	def validate_filing_details(self, rules):
		missing = [
			_(self.meta.get_label(fieldname))
			for fieldname in ("filed_on", "acknowledgement_number")
			if not self.get(fieldname)
		]
		if rules.requires_proof and not self.proof:
			missing.append(_("Proof"))
		if missing:
			frappe.throw(
				_("Fill in {0} before moving {1} to {2}.").format(
					", ".join(missing), self.name, _(self.status)
				)
			)

	def mark_filed(self, rules):
		user = frappe.session.user
		if rules.requires_review:
			if user == self.responsible:
				frappe.throw(
					_("{0} prepared {1}, so someone else must check it and mark it filed.").format(
						user, self.name
					),
					frappe.PermissionError,
				)
			if user != self.reviewer and not is_approver():
				frappe.throw(
					_("Only the reviewer or a Compliance Manager can mark {0} filed.").format(self.name),
					frappe.PermissionError,
				)
			self.reviewed_by = user
		late = getdate(self.filed_on) > getdate(self.effective_due_date)
		self.status = "Filed Late" if late else "Filed"
