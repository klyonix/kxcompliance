# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_years, cint, flt, getdate, nowdate

from kxcompliance import scoped
from kxcompliance.kx_compliance.register import (
	CLOSED_TASK_STATUSES,
	TIME_BARRED,
	check_reassignment,
	is_approver,
)

FILED_STATUSES = ("Filed", "Filed Late")
# Statuses of a filing not yet made on the portal: an earlier one blocks filing in period order.
NOT_YET_FILED = ("Open", "In Progress")
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
		self.set_time_bar()
		before = self.get_doc_before_save()
		previous = before.status if before else None
		if before:
			self.protect_schedule(before)
		if self.is_nil:
			self.validate_nil()
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

	def set_time_bar(self):
		"""The last day the return can be filed, and whether that has passed for one still to file."""
		rules = frappe.get_cached_doc("Compliance Obligation Template", self.obligation_template)
		years = cint(rules.time_bar_years)
		self.last_filing_date = (
			add_years(self.effective_due_date, years) if years and self.effective_due_date else None
		)
		self.is_time_barred = int(
			is_time_barred(self.last_filing_date, self.status, self.filed_on, getdate(nowdate()))
		)

	def check_closing_as_time_barred(self, previous: str | None):
		"""A manager closes a filing the portal no longer accepts, saying why; only one past its last day."""
		if not is_approver():
			frappe.throw(
				_("Only a Compliance Manager can close {0} as time-barred.").format(self.name),
				frappe.PermissionError,
			)
		if not is_time_barred(self.last_filing_date, previous or "Open", self.filed_on, getdate(nowdate())):
			frappe.throw(
				_("{0} is not time-barred: it can still be filed until {1}.").format(
					self.name,
					frappe.format(self.last_filing_date, "Date") if self.last_filing_date else _("any time"),
				)
			)
		if not (self.remarks or "").strip():
			frappe.throw(_("Say in Remarks why {0} was not filed in time.").format(self.name))

	def check_time_bar(self):
		if (
			self.last_filing_date
			and self.filed_on
			and getdate(self.filed_on) > getdate(self.last_filing_date)
		):
			frappe.throw(
				_(
					"{0} is time-barred: it could be filed only until {1}, so it cannot be recorded as "
					"filed on {2}. If it was filed by then, correct Filed On."
				).format(
					self.name,
					frappe.format(self.last_filing_date, "Date"),
					frappe.format(self.filed_on, "Date"),
				),
				title=_("Time-barred return"),
			)

	def validate_nil(self):
		rules = frappe.get_cached_doc("Compliance Obligation Template", self.obligation_template)
		if not rules.allows_nil:
			frappe.throw(_("{0} cannot be filed as a NIL return.").format(self.obligation_template))
		# A late fee may still be paid on a NIL return filed late; tax and interest may not.
		paid = [
			_(self.meta.get_label(fieldname))
			for fieldname in ("amount_paid", "interest")
			if flt(self.get(fieldname))
		]
		if paid:
			frappe.throw(
				_("{0} is a NIL return, so {1} must be 0. Untick NIL Return if something was paid.").format(
					self.name, ", ".join(paid)
				)
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
			self.check_time_bar()
			if rules.files_in_order:
				self.check_period_order(rules)
			if rules.filed_after_form:
				self.check_filed_after(rules)
		if self.status in FILED_STATUSES:
			self.mark_filed(rules)
		if self.status == TIME_BARRED:
			self.check_closing_as_time_barred(previous)
		if self.status == "Not Applicable" and not (self.remarks or "").strip():
			frappe.throw(_("Say in Remarks why {0} does not apply.").format(self.name))
		if self.status == "Cancelled" and not is_approver():
			frappe.throw(
				_("Only a Compliance Manager can cancel {0}.").format(self.name), frappe.PermissionError
			)

	def validate_filing_details(self, rules):
		# A NIL period that gives no acknowledgement (a TDS non-filing declaration) needs only its date.
		declared = self.is_nil and not rules.nil_needs_acknowledgement
		required = ("filed_on",) if declared else ("filed_on", "acknowledgement_number")
		missing = [_(self.meta.get_label(fieldname)) for fieldname in required if not self.get(fieldname)]
		if rules.requires_proof and not declared and not self.proof:
			missing.append(_("Proof"))
		if missing:
			frappe.throw(
				_("Fill in {0} before moving {1} to {2}.").format(
					", ".join(missing), self.name, _(self.status)
				)
			)

	def check_period_order(self, rules):
		"""Refuse a period while an earlier one of the same return and registration is still to file.

		The same return may be on more than one obligation (GSTR-3B monthly and quarterly, for a
		company that moved to QRMP): every in-order obligation for that form counts.
		"""
		series = return_series(rules)
		earlier = scoped.get_all(
			"Compliance Task",
			filters={
				"obligation_template": ("in", series),
				"company": self.company,
				"registration_number": self.registration_number or ("is", "not set"),
				"period_end": ("<", self.period_end),
				"status": ("in", NOT_YET_FILED),
				"name": ("!=", self.name),
			},
			fields=["name", "obligation_template", "period_label"],
			order_by="period_end asc",
			limit=1,
		)
		if earlier:
			frappe.throw(
				_(
					"{0} ({1}, {2}) must be filed first: {3} files in period order, so {4} cannot move to {5}."
				).format(
					earlier[0].name,
					earlier[0].obligation_template,
					earlier[0].period_label,
					rules.form or self.obligation_template,
					self.name,
					_(self.status),
				),
				title=_("Earlier period to file"),
			)

	def check_filed_after(self, rules):
		"""Refuse this period while the same period's other return, which must go first, is still to file.

		For GSTR-3B that is GSTR-1, monthly or quarterly: any of its periods within this one counts.
		"""
		if not (self.period_start and self.period_end):
			return
		first = scoped.get_all(
			"Compliance Obligation Template",
			filters={"law": rules.law, "form": rules.filed_after_form},
			pluck="name",
		)
		if not first:
			return
		pending = scoped.get_all(
			"Compliance Task",
			filters={
				"obligation_template": ("in", first),
				"company": self.company,
				"registration_number": self.registration_number or ("is", "not set"),
				"period_end": ("between", [self.period_start, self.period_end]),
				"status": ("in", NOT_YET_FILED),
				"name": ("!=", self.name),
			},
			fields=["name", "obligation_template", "period_label"],
			order_by="period_end asc",
			limit=1,
		)
		if pending:
			frappe.throw(
				_(
					"{0} ({1}, {2}) must be filed first: {3} is filed only after the same period's {4}, "
					"so {5} cannot move to {6}."
				).format(
					pending[0].name,
					pending[0].obligation_template,
					pending[0].period_label,
					rules.form or self.obligation_template,
					rules.filed_after_form,
					self.name,
					_(self.status),
				),
				title=_("{0} to file first").format(rules.filed_after_form),
			)

	def checks_own_filing(self, user: str) -> bool:
		"""A Compliance Manager who prepared this filing and has no one else set to check it."""
		return user == self.responsible and self.reviewer in (None, "", user) and is_approver(user)

	def mark_filed(self, rules):
		user = frappe.session.user
		self.filed_without_check = 0
		if rules.requires_review:
			if self.checks_own_filing(user):
				# A one-person team: a manager with no one else to check their filing files it, and
				# the filing says so.
				self.filed_without_check = 1
			elif user == self.responsible:
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


def return_series(rules) -> list[str]:
	"""The obligations filed as one series with this one: the in-order ones for the same law and form."""
	if not rules.form:
		return [rules.name]
	names = scoped.get_all(
		"Compliance Obligation Template",
		filters={"law": rules.law, "form": rules.form, "files_in_order": 1},
		pluck="name",
	)
	return names or [rules.name]


def is_time_barred(last_filing_date, status: str, filed_on, today) -> bool:
	"""Past its last day to file, still open, and not recorded as filed by that day."""
	if not last_filing_date or status in CLOSED_TASK_STATUSES:
		return False
	if filed_on and getdate(filed_on) <= getdate(last_filing_date):
		return False
	return getdate(last_filing_date) < getdate(today)
