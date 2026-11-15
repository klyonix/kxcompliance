# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime

from kxcompliance.kx_compliance.privacy import board_due_by

DATE_FIELDS = ("board_reported_on", "people_informed_on")


class PersonalDataBreach(Document):
	def validate(self):
		discovered = get_datetime(self.discovered_on)
		if discovered > now_datetime():
			frappe.throw(_("Discovered On cannot be in the future ({0}).").format(self.discovered_on))
		for field in DATE_FIELDS:
			value = self.get(field)
			if not value:
				continue
			if get_datetime(value) < discovered:
				frappe.throw(
					_("{0} ({1}) cannot be before the breach was discovered ({2}).").format(
						_(self.meta.get_label(field)), value, self.discovered_on
					)
				)
			if get_datetime(value) > now_datetime():
				frappe.throw(
					_("{0} cannot be in the future ({1}).").format(_(self.meta.get_label(field)), value)
				)
		self.board_due_by = board_due_by(self.discovered_on)
		if not self.board_reported_on:
			self.status = "Board not told"
		elif not self.people_informed_on:
			self.status = "People not told"
		else:
			self.status = "Reported"
