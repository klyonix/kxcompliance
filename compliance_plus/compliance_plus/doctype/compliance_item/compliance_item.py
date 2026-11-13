# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from compliance_plus.compliance_plus.register import (
	compute_status,
	due_soon_days,
	get_type_rules,
	items_with_applied_renewal,
)


class ComplianceItem(Document):
	def validate(self):
		rules = get_type_rules([self.item_type]).get(self.item_type) or frappe._dict()
		self.set_holder()
		if self.is_new():
			self.copy_reminders_from_type()
		self.validate_dates(rules)
		self.status = self.get_status(rules)

	def set_holder(self):
		if self.holder_type == "Company":
			self.holder = self.company
		elif not self.holder:
			frappe.throw(_("Choose the {0} that holds this item.").format(_(self.holder_type)))

	def copy_reminders_from_type(self):
		if self.reminders or not self.item_type:
			return
		type_doc = frappe.get_cached_doc("Compliance Item Type", self.item_type)
		for rule in type_doc.reminders:
			self.append("reminders", {"days_before": rule.days_before})

	def validate_dates(self, rules: frappe._dict):
		if rules.renewal_cycle_months and not self.valid_until:
			frappe.throw(
				_("Valid Until is required, because items of type {0} expire.").format(
					frappe.bold(self.item_type)
				)
			)
		if not self.valid_until:
			return
		for fieldname in ("valid_from", "issue_date"):
			value = self.get(fieldname)
			if value and getdate(value) > getdate(self.valid_until):
				frappe.throw(
					_("{0} ({1}) cannot be after Valid Until ({2}).").format(
						_(self.meta.get_label(fieldname)),
						frappe.format(value, "Date"),
						frappe.format(self.valid_until, "Date"),
					)
				)

	def get_status(self, rules: frappe._dict) -> str:
		renewal_applied = not self.is_new() and self.name in items_with_applied_renewal([self.name])
		return compute_status(
			is_cancelled=bool(self.is_cancelled),
			valid_until=self.valid_until,
			has_certificate=bool(self.certificate),
			requires_document=bool(rules.requires_document),
			renewal_applied=renewal_applied,
			grace_days=rules.grace_days or 0,
			today=nowdate(),
			soon_days=due_soon_days(),
		)

	@frappe.whitelist(methods=["POST"])
	def cancel_item(self, reason: str):
		self.check_permission("write")
		if self.is_cancelled:
			frappe.throw(_("{0} is already cancelled.").format(self.name))
		reason = (reason or "").strip()
		if not reason:
			frappe.throw(_("Give a reason for cancelling {0}.").format(self.name))
		self.is_cancelled = 1
		self.cancellation_reason = reason
		self.save()
