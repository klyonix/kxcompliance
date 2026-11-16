# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document

from kxcompliance import scoped

DIN_PATTERN = re.compile(r"^\d{8}$")
PAN_PATTERN = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$")


class Signatory(Document):
	def validate(self):
		self.full_name = (self.full_name or "").strip()
		self.din = (self.din or "").strip()
		self.pan = (self.pan or "").strip().upper()
		if self.din and not DIN_PATTERN.match(self.din):
			frappe.throw(_("DIN / DPIN {0} should be 8 digits.").format(self.din))
		if self.pan and not PAN_PATTERN.match(self.pan):
			frappe.throw(_("PAN {0} should look like ABCDE1234F.").format(self.pan))
		self.validate_companies()
		self.validate_unique_din()

	def validate_companies(self):
		seen = {self.company}
		for row in self.other_companies:
			if row.company in seen:
				frappe.throw(
					_("Other Companies row {0}: {1} is already listed for {2}.").format(
						row.idx, row.company, self.full_name
					)
				)
			seen.add(row.company)

	def validate_unique_din(self):
		if not self.din:
			return
		other = scoped.get_value(
			"Signatory", {"din": self.din, "company": self.company, "name": ("!=", self.name)}, "full_name"
		)
		if other:
			frappe.throw(
				_("DIN {0} is already recorded for {1} at {2}; add {2} to that signatory instead.").format(
					self.din, other, self.company
				)
			)

	def companies(self) -> set[str]:
		return {self.company} | {row.company for row in self.other_companies}


@frappe.whitelist(methods=["GET"])
@frappe.validate_and_sanitize_search_inputs
def signatories_for(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	"""Active signatories who sign for a company, for the holder of a DSC."""
	frappe.has_permission("Signatory", "read", throw=True)
	company = (filters or {}).get("company")
	if not company:
		return []
	other = frappe.get_list(
		"Signatory Company", filters={"company": company}, pluck="parent", parent_doctype="Signatory"
	)
	return frappe.get_list(
		"Signatory",
		filters={"is_active": 1, "full_name": ("like", f"%{txt}%")},
		or_filters={"company": company, "name": ("in", other or [""])},
		fields=["name", "full_name", "designation"],
		order_by="full_name asc",
		limit_start=start,
		limit_page_length=page_len,
		as_list=True,
	)
