# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from kxcompliance.kx_compliance.billing import check_rate_lines, keep_one_default


class RateCard(Document):
	def validate(self):
		check_rate_lines(self.lines, self.title)

	def on_update(self):
		keep_one_default(self)
