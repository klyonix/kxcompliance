# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ComplianceTourView(Document):
	def autoname(self):
		# One row per person and tour; the name keeps it so, even when two tabs open it at once.
		self.name = f"{self.user}:{self.tour}"
