# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

from frappe.model.document import Document

GROUP_TYPES = {"Customer": "Customer Group", "Supplier": "Supplier Group"}


class LicenceRequirement(Document):
	def validate(self):
		for row in self.party_groups:
			row.group_type = GROUP_TYPES[self.party_type]
