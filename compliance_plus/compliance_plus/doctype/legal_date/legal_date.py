# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from compliance_plus.compliance_plus.legal import REFERENCE_COMPANIES, REFERENCE_TITLES, refresh_next_date

OUTCOME_STATUSES = ("Done", "Adjourned")


class LegalDate(Document):
	def validate(self):
		if self.reference_doctype not in REFERENCE_TITLES:
			frappe.throw(
				_("A Legal Date belongs to one of {0}, not {1}.").format(
					", ".join(REFERENCE_TITLES), self.reference_doctype
				)
			)
		reference = frappe.db.get_value(
			self.reference_doctype,
			self.reference_name,
			[
				REFERENCE_TITLES[self.reference_doctype],
				f"{REFERENCE_COMPANIES[self.reference_doctype]} as company",
				"responsible",
				"reviewer",
			],
			as_dict=True,
		)
		if not reference:
			frappe.throw(_("{0} {1} does not exist.").format(_(self.reference_doctype), self.reference_name))
		self.reference_title = reference[REFERENCE_TITLES[self.reference_doctype]]
		self.company = reference.company
		self.responsible = reference.responsible
		self.reviewer = reference.reviewer
		if (
			self.kind == "Hearing"
			and self.status in OUTCOME_STATUSES
			and not (self.proceedings or "").strip()
		):
			frappe.throw(
				_("Write what happened at the hearing before marking it {0}.").format(_(self.status))
			)
		if self.next_date and getdate(self.next_date) <= getdate(self.date):
			frappe.throw(
				_("Next Date ({0}) must be after this date ({1}).").format(
					frappe.format(self.next_date, "Date"), frappe.format(self.date, "Date")
				)
			)
		self.is_overdue = int(self.status == "Scheduled" and getdate(self.date) < getdate(nowdate()))

	def on_update(self):
		if self.status in OUTCOME_STATUSES and self.next_date and not self.next_legal_date:
			self.make_next_date()
		refresh_next_date(self.reference_doctype, self.reference_name)

	def after_delete(self):
		refresh_next_date(self.reference_doctype, self.reference_name)

	def make_next_date(self):
		next_doc = frappe.get_doc(
			{
				"doctype": "Legal Date",
				"reference_doctype": self.reference_doctype,
				"reference_name": self.reference_name,
				"kind": self.kind,
				"date": self.next_date,
				"purpose": _("Continued from {0}").format(frappe.format(self.date, "Date")),
			}
		).insert()
		self.db_set("next_legal_date", next_doc.name)
