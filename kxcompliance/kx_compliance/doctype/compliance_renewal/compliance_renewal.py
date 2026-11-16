# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from kxcompliance import scoped
from kxcompliance.kx_compliance.register import (
	OPEN_RENEWAL_STATUSES,
	get_type_rules,
	is_approver,
)

CLOSED_STATUSES = ("Approved", "Rejected", "Withdrawn")


class ComplianceRenewal(Document):
	def validate(self):
		item = frappe.get_doc("Compliance Item", self.compliance_item)
		previous_status = self.get_previous_status()

		self.validate_item_open(item, previous_status)
		self.validate_status_change(previous_status)
		self.validate_single_open_renewal()
		if self.status == "Applied" and not self.applied_on:
			self.applied_on = nowdate()
		if self.status == "Approved" and previous_status != "Approved":
			self.validate_approval(item)
			self.record_previous_validity(item)
		self.open_key = self.compliance_item if self.status in OPEN_RENEWAL_STATUSES else None

	def on_update(self):
		if self.get_previous_status() == self.status:
			return
		item = frappe.get_doc("Compliance Item", self.compliance_item)
		if self.status == "Approved":
			item.valid_from = self.new_valid_from
			item.valid_until = self.new_valid_until
			if self.new_certificate:
				item.certificate = self.new_certificate
		item.save()

	def on_trash(self):
		if self.status == "Approved":
			frappe.throw(_("{0} is approved and is part of the item's history.").format(self.name))

	def get_previous_status(self) -> str | None:
		before = self.get_doc_before_save()
		return before.status if before else None

	def validate_item_open(self, item, previous_status):
		if item.is_cancelled and self.status in OPEN_RENEWAL_STATUSES and previous_status is None:
			frappe.throw(_("{0} is cancelled and cannot be renewed.").format(item.name))

	def validate_status_change(self, previous_status):
		if previous_status in CLOSED_STATUSES and self.status != previous_status:
			frappe.throw(
				_("{0} is {1} and its status cannot change to {2}.").format(
					self.name, _(previous_status), _(self.status)
				)
			)

	def validate_single_open_renewal(self):
		# A friendly message first; the unique open_key column is what actually stops two at once.
		if self.status not in OPEN_RENEWAL_STATUSES:
			return
		other = scoped.get_value(
			"Compliance Renewal",
			{
				"compliance_item": self.compliance_item,
				"status": ("in", OPEN_RENEWAL_STATUSES),
				"name": ("!=", self.name or ""),
			},
			"name",
		)
		if other:
			frappe.throw(
				_("{0} already has an open renewal, {1}. Close it before starting another.").format(
					self.compliance_item, other
				)
			)

	def validate_approval(self, item):
		if not is_approver():
			frappe.throw(
				_("Only a Compliance Manager can approve {0}.").format(self.name),
				frappe.PermissionError,
			)
		rules = get_type_rules([item.item_type]).get(item.item_type) or frappe._dict()
		if rules.renewal_cycle_months and not self.new_valid_until:
			frappe.throw(_("Set New Valid Until before approving."))
		if rules.requires_document and not self.new_certificate:
			frappe.throw(_("Attach the New Certificate before approving."))
		if self.new_valid_from and self.new_valid_until:
			if getdate(self.new_valid_from) > getdate(self.new_valid_until):
				frappe.throw(
					_("New Valid From ({0}) cannot be after New Valid Until ({1}).").format(
						frappe.format(self.new_valid_from, "Date"),
						frappe.format(self.new_valid_until, "Date"),
					)
				)
		if item.valid_until and self.new_valid_until:
			if getdate(self.new_valid_until) <= getdate(item.valid_until):
				frappe.throw(
					_("New Valid Until ({0}) must be after the current Valid Until ({1}).").format(
						frappe.format(self.new_valid_until, "Date"),
						frappe.format(item.valid_until, "Date"),
					)
				)

	def record_previous_validity(self, item):
		self.previous_valid_from = item.valid_from
		self.previous_valid_until = item.valid_until
		self.previous_certificate = item.certificate
