# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model import display_fieldtypes, table_fields
from frappe.model.document import Document
from frappe.utils import cint, flt

# What a firm may change on a standard template; every update brings the rest back to the library.
# Its own late-filing figures are kept apart, in Compliance Penalty Figures (penalty_figures.py).
FIRM_FIELDS = {"is_active"}


class ComplianceObligationTemplate(Document):
	def validate(self):
		self.keep_standard_rules()
		if self.due_after_event:
			# After a company event when an Event Type is set; otherwise after the AGM.
			self.frequency = "Per Event" if self.event_type else "Yearly"
			self.period_basis = "Financial Year"
			if not self.days_after_event:
				frappe.throw(
					_("Set how many days after the {0} {1} is due.").format(
						_(self.event_type) if self.event_type else _("AGM"), self.template_name
					)
				)
		elif self.event_type or self.frequency == "Per Event":
			frappe.throw(
				_("{0} has an Event Type or the Per Event frequency, so tick Due After an Event.").format(
					self.template_name
				)
			)
		elif not 1 <= (self.due_day or 0) <= 31:
			frappe.throw(_("Due Day must be between 1 and 31, not {0}.").format(self.due_day))
		self.skipped_months()
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

	def skipped_months(self) -> set[int]:
		"""The months listed in Skipped Months, in which no period of a monthly obligation is due."""
		months = set()
		for part in (self.skip_months or "").replace(" ", "").split(","):
			if not part:
				continue
			if not part.isdigit() or not 1 <= int(part) <= 12:
				frappe.throw(
					_(
						"Skipped Months must be month numbers from 1 to 12 with commas between, not {0}."
					).format(part)
				)
			months.add(int(part))
		if months and self.frequency != "Monthly":
			frappe.throw(
				_("Only a monthly obligation can skip months; {0} is {1}.").format(
					self.template_name, _(self.frequency)
				)
			)
		return months

	def state_list(self) -> set[str]:
		return {line.strip() for line in (self.states or "").splitlines() if line.strip()}

	def keep_standard_rules(self):
		"""Refuse changes to a standard template's rules, which the next update would undo anyway.

		Its on/off switch is the firm's; only the library itself (flags.from_library) writes the rest.
		"""
		if self.flags.from_library:
			return
		if self.is_new():
			self.is_standard = 0
			return
		before = self.get_doc_before_save()
		if not self.is_standard or not before:
			return
		changed = [
			_(df.label)
			for df in self.meta.fields
			if df.fieldname not in FIRM_FIELDS
			and df.fieldtype not in display_fieldtypes
			and comparable(before, df) != comparable(self, df)
		]
		if changed:
			frappe.throw(
				_(
					"{0} is a standard obligation, so updates keep its rules. Only In Use can be "
					"changed, not {1}. Keep your own late-filing figures for it, or add your own "
					"obligation for a different rule."
				).format(self.name, ", ".join(changed)),
				title=_("Standard obligation"),
			)


def comparable(doc, df):
	"""A field's value in a form that compares equal whether it came from the database or the app."""
	value = doc.get(df.fieldname)
	if df.fieldtype in table_fields:
		fields = [
			field for field in frappe.get_meta(df.options).fields if field.fieldtype not in display_fieldtypes
		]
		return [tuple(comparable(row, field) for field in fields) for row in value or []]
	if df.fieldtype in ("Check", "Int"):
		return cint(value)
	if df.fieldtype in ("Float", "Currency", "Percent"):
		return flt(value)
	return str(value or "").strip()
