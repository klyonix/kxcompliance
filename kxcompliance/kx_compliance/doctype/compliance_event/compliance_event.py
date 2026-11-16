# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from kxcompliance import scoped
from kxcompliance.kx_compliance.company_events import event_types_for, make_event_tasks
from kxcompliance.kx_compliance.register import CLOSED_TASK_STATUSES, is_approver


class ComplianceEvent(Document):
	def validate(self):
		if not self.is_new():
			return
		self.status = "Recorded"
		self.recorded_by = frappe.session.user
		if getdate(self.event_date) > getdate(nowdate()):
			frappe.throw(
				_("Record {0} once it has happened; {1} is in the future.").format(
					_(self.event_type), frappe.format(self.event_date, "Date")
				)
			)
		profile = scoped.get_value(
			"Company Compliance Profile", self.company, ["company_type", "default_responsible"], as_dict=True
		)
		if not profile:
			frappe.throw(
				_("Set up the Company Compliance Profile for {0} before recording its events.").format(
					self.company
				)
			)
		if self.event_type not in event_types_for(profile.company_type):
			frappe.throw(
				_("{0} calls for no filing from a {1} such as {2}; choose another event.").format(
					_(self.event_type), _(profile.company_type), self.company
				)
			)
		if not profile.default_responsible:
			frappe.throw(
				_(
					"Set a Default Responsible on {0}'s Company Compliance Profile; its filings go to them."
				).format(self.company)
			)

	def after_insert(self):
		make_event_tasks(self)

	@frappe.whitelist(methods=["GET"])
	def filings(self) -> list[dict]:
		"""What this event made due, for whoever can read the event, such as the person who recorded it."""
		self.check_permission("read")
		# The event's own filings, by form and due date only; the tasks themselves keep their permissions.
		return scoped.get_all(
			"Compliance Task",
			filters={"company_event": self.name},
			fields=["name", "obligation_template", "effective_due_date", "status"],
			order_by="effective_due_date asc",
		)

	@frappe.whitelist(methods=["POST"])
	def cancel_event(self, reason: str):
		"""Withdraw an event recorded by mistake, and cancel the filings it created that are still open."""
		self.check_permission("write")
		if not is_approver():
			frappe.throw(
				_("Only a Compliance Manager can cancel {0}.").format(self.name), frappe.PermissionError
			)
		if self.status == "Cancelled":
			frappe.throw(_("{0} is already cancelled.").format(self.name))
		if not (reason or "").strip():
			frappe.throw(_("Say why {0} is being cancelled.").format(self.name))
		for name in scoped.get_all(
			"Compliance Task",
			filters={"company_event": self.name, "status": ("not in", CLOSED_TASK_STATUSES)},
			pluck="name",
		):
			task = frappe.get_doc("Compliance Task", name)
			task.status = "Cancelled"
			task.remarks = _("Cancelled with event {0}: {1}").format(self.name, reason.strip())
			task.save()
		self.status = "Cancelled"
		self.cancellation_reason = reason.strip()
		self.save()
