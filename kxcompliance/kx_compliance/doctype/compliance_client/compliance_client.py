# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from kxcompliance.kx_compliance.billing import check_fee_plan, check_return_fees, state_of
from kxcompliance.kx_compliance.clients import (
	sync_client_access,
	sync_client_logins,
	turn_logins_off,
	validate_logins,
)


class ComplianceClient(Document):
	def validate(self):
		seen = set()
		for row in self.team:
			if row.user in seen:
				frappe.throw(_("Team row {0}: {1} is already on the team.").format(row.idx, row.user))
			seen.add(row.user)
		validate_logins(self)
		# Bills charge GST by the client's state, which its GSTIN says when it has one.
		self.gstin = (self.gstin or "").strip().upper() or None
		self.billing_state = state_of(self.gstin, self.billing_state)
		check_fee_plan(self)
		check_return_fees(self.return_fees, _("Own Price per Return"))

	def on_update(self):
		# Logins first, so their users exist when the access is given.
		sync_client_logins(self)
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
		turn_logins_off({row.user for row in self.logins if row.user}, self.name)
