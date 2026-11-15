# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
from frappe.model.document import Document
from frappe.utils import add_days, getdate, now_datetime

from kxcompliance.kx_compliance.privacy import RESPONSE_DAYS
from kxcompliance.kx_compliance.reminders import compliance_managers, send_email

CLOSED = ("Done", "Declined")


class PrivacyRequest(Document):
	def before_insert(self):
		self.status = "Open"
		self.received_on = now_datetime()
		self.due_by = add_days(getdate(self.received_on), RESPONSE_DAYS)

	def validate(self):
		if self.status in CLOSED:
			if not (self.response or "").strip():
				frappe.throw(
					_("Write the response to {0} before marking request {1} {2}.").format(
						self.requester_name or self.requested_by, self.name, _(self.status)
					)
				)
			if not self.closed_on:
				self.closed_on = now_datetime()
				self.closed_by = frappe.session.user
		else:
			self.closed_on = None
			self.closed_by = None

	def after_insert(self):
		recipients = [user for user in compliance_managers() if user != self.requested_by]
		if recipients:
			enqueue_create_notification(
				recipients,
				{
					"type": "Alert",
					"document_type": self.doctype,
					"document_name": self.name,
					"subject": _("{0} asked: {1}. Answer by {2}.").format(
						frappe.utils.escape_html(self.requester_name or self.requested_by),
						_(self.request_type),
						frappe.utils.formatdate(self.due_by),
					),
				},
			)

	def on_update(self):
		# The person is told the answer once, when the request is closed: in the app, and by email
		# when the app sends email.
		before = self.get_doc_before_save()
		if self.status not in CLOSED or (before and before.status in CLOSED):
			return
		subject = _("Your privacy request {0} is {1}").format(self.name, _(self.status).lower())
		enqueue_create_notification(
			self.requested_by,
			{
				"type": "Alert",
				"document_type": self.doctype,
				"document_name": self.name,
				"subject": subject,
				"email_content": frappe.utils.escape_html(self.response),
			},
		)
		send_email(
			[self.requested_by],
			subject,
			frappe.utils.escape_html(self.response).replace("\n", "<br>"),
			self.doctype,
			self.name,
		)
