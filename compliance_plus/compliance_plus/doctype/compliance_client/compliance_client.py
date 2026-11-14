# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from compliance_plus.compliance_plus.clients import sync_client_access


class ComplianceClient(Document):
	def validate(self):
		seen = set()
		for row in self.team:
			if row.user in seen:
				frappe.throw(_("Team row {0}: {1} is already on the team.").format(row.idx, row.user))
			seen.add(row.user)

	def on_update(self):
		sync_client_access(self.name)

	def on_trash(self):
		if frappe.db.exists("Company Compliance Profile", {"client": self.name}):
			frappe.throw(
				_("{0} still owns companies; move them to another client or mark the client Left.").format(
					self.name
				)
			)

	def after_delete(self):
		sync_client_access(self.name)
