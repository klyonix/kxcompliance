# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ComplianceObligationTemplate(Document):
	def validate(self):
		if self.due_after_event:
			self.frequency = "Yearly"
			self.period_basis = "Financial Year"
		elif not 1 <= (self.due_day or 0) <= 31:
			frappe.throw(_("Due Day must be between 1 and 31, not {0}.").format(self.due_day))
		for row in self.overrides:
			if not 1 <= (row.period_end_month or 0) <= 12:
				frappe.throw(
					_("Exceptions row {0}: the month must be between 1 and 12, not {1}.").format(
						row.idx, row.period_end_month
					)
				)
			if not 1 <= (row.due_day or 0) <= 31:
				frappe.throw(
					_("Exceptions row {0}: the due day must be between 1 and 31, not {1}.").format(
						row.idx, row.due_day
					)
				)

	def applies_to(self, company_type: str) -> bool:
		types = {row.company_type for row in self.company_types}
		return not types or company_type in types

	def state_list(self) -> set[str]:
		return {line.strip() for line in (self.states or "").splitlines() if line.strip()}
