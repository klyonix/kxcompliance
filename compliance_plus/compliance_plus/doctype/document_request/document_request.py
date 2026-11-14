# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, nowdate

from compliance_plus.compliance_plus import document_requests


class DocumentRequest(Document):
	def validate(self):
		self.set_company_and_client()
		if self.is_new():
			self.status = "Requested"
			self.requested_by = frappe.session.user
		elif self.has_value_changed("status") and not self.flags.status_change:
			frappe.throw(
				_(
					"Status of {0} changes only by uploading, accepting, sending back or withdrawing it."
				).format(self.name)
			)
		self.is_overdue = int(self.status == "Requested" and getdate(self.due_date) < getdate(nowdate()))

	def set_company_and_client(self):
		self.filing_label = ""
		if self.compliance_task:
			task_company, template, period = frappe.db.get_value(
				"Compliance Task", self.compliance_task, ["company", "obligation_template", "period_label"]
			) or (None, None, None)
			self.filing_label = f"{template} ({period})" if period else (template or "")
			if self.company and task_company and self.company != task_company:
				frappe.throw(
					_("Filing {0} is for {1}, not {2}.").format(
						self.compliance_task, task_company, self.company
					)
				)
			self.company = task_company or self.company
		if not self.company:
			return  # the mandatory check names the missing Company
		self.client = frappe.db.get_value("Company Compliance Profile", self.company, "client")
		if not self.client:
			frappe.throw(
				_(
					"{0} is not linked to a client. Set the client on its Company Compliance Profile first."
				).format(self.company)
			)

	def after_insert(self):
		document_requests.asked(self)

	def change_status(self, status: str, allowed_from: tuple[str, ...]):
		self.check_permission("write")
		if self.status not in allowed_from:
			frappe.throw(_("{0} is {1}, so it cannot be marked {2}.").format(self.name, self.status, status))
		self.status = status
		self.flags.status_change = True

	@frappe.whitelist(methods=["POST"])
	def accept(self):
		self.change_status("Accepted", ("Uploaded",))
		self.accepted_by = frappe.session.user
		self.accepted_on = now_datetime()
		self.save()

	@frappe.whitelist(methods=["POST"])
	def send_back(self, note: str):
		note = (note or "").strip()
		if not note:
			frappe.throw(_("Say what is wrong with the upload, so the client can send the right document."))
		self.change_status("Requested", ("Uploaded",))
		self.firm_note = note
		self.save()
		document_requests.sent_back(self)

	@frappe.whitelist(methods=["POST"])
	def withdraw(self):
		self.change_status("Withdrawn", document_requests.OPEN_STATUSES)
		self.save()
