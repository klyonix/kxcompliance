# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from kxcompliance import scoped
from kxcompliance.kx_compliance.billing import check_client_rates, follow_client, state_of
from kxcompliance.kx_compliance.clients import (
	sync_client_access,
	sync_client_logins,
	turn_logins_off,
	validate_logins,
)


class ComplianceClient(Document):
	def before_insert(self):
		scoped.check_limit("Compliance Client", client_name=self.client_name)

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
		check_client_rates(self)
		self.check_recurring_company()

	def check_recurring_company(self):
		"""Recurring charges go on the bills of one of the client's own companies."""
		if self.recurring_company and not scoped.exists(
			"Company Compliance Profile", {"company": self.recurring_company, "client": self.name}
		):
			frappe.throw(
				_("Bill recurring charges to: {0} is not one of {1}'s companies.").format(
					self.recurring_company, self.name
				)
			)

	def on_update(self):
		# Logins first, so their users exist when the access is given.
		sync_client_logins(self)
		sync_client_access(self.name)
		follow_client(self)

	def on_trash(self):
		if scoped.exists("Company Compliance Profile", {"client": self.name}):
			frappe.throw(
				_("{0} still owns companies; move them to another client or mark the client Left.").format(
					self.client_name
				)
			)

	def after_delete(self):
		sync_client_access(self.name)
		turn_logins_off({row.user for row in self.logins if row.user}, self.name)
