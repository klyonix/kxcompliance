# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

DSC_TYPE = "Digital Signature Certificate"
CUSTODY_STATES = ("With the Firm", "With the Client", "With the Holder", "Not Known")

from compliance_plus.compliance_plus.doctype.trademark.trademark import follow_renewal
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
		self.set_custody()
		if self.is_new():
			self.copy_reminders_from_type()
		self.validate_dates(rules)
		self.status = self.get_status(rules)

	def set_holder(self):
		self.holder_name = ""
		if self.holder_type == "Company":
			self.holder = self.company
			return
		if not self.holder:
			frappe.throw(_("Choose the {0} that holds this item.").format(_(self.holder_type)))
		if self.holder_type == "Signatory":
			self.check_signatory()

	def check_signatory(self):
		signatory = frappe.get_doc("Signatory", self.holder)
		self.holder_name = signatory.full_name
		if self.company not in signatory.companies():
			frappe.throw(
				_(
					"{0} does not sign for {1}. Add {1} to the signatory's companies, or pick their company."
				).format(signatory.full_name, self.company)
			)

	def set_custody(self):
		"""Where the token is now: the latest hand-over."""
		if not self.custody_log:
			return
		latest = max(self.custody_log, key=lambda row: (getdate(row.on_date), row.idx))
		self.custody = latest.custody
		self.custody_since = latest.on_date

	@frappe.whitelist(methods=["POST"])
	def hand_over(self, custody: str, person: str | None = None, note: str | None = None):
		"""Record that the DSC's token changed hands."""
		self.check_permission("write")
		if self.item_type != DSC_TYPE:
			frappe.throw(_("{0} is not a digital signature, so it has no token.").format(self.name))
		if custody not in CUSTODY_STATES:
			frappe.throw(_("Token Now should be one of: {0}.").format(", ".join(CUSTODY_STATES)))
		self.append(
			"custody_log",
			{
				"on_date": nowdate(),
				"custody": custody,
				"person": (person or "").strip(),
				"note": (note or "").strip(),
				"recorded_by": frappe.session.user,
			},
		)
		self.save()

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

	def on_update(self):
		if self.has_value_changed("valid_until"):
			follow_renewal(self)

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
