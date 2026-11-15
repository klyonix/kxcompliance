# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Views people save of the app's lists (RK, 15 Nov 2026).

Each person sees their own views and the shared ones, and changes only their own; a Compliance
Manager may also share, pin, change and delete shared views. Who sees and changes which is in
kxcompliance/permissions.py, as it turns on who made the view.
"""

import json

import frappe
from frappe import _
from frappe.model.document import Document

from kxcompliance.kx_compliance.register import is_approver

LAYOUTS = ("List", "Table", "Kanban")
LABEL_MAX = 60
JSON_FIELDS = ("filters", "columns", "quick_filters")


class ComplianceListView(Document):
	def validate(self):
		self.label = (self.label or "").strip()
		if not self.label:
			frappe.throw(_("Give the view a name."))
		if len(self.label) > LABEL_MAX:
			frappe.throw(_("Keep the view's name under {0} characters.").format(LABEL_MAX))
		for field in JSON_FIELDS:
			value = self.get(field)
			if isinstance(value, str) and value:
				try:
					json.loads(value)
				except ValueError:
					frappe.throw(
						_("{0} of view {1} is not valid.").format(_(self.meta.get_label(field)), self.label)
					)
		if self.layout == "Kanban" and not self.board:
			frappe.throw(_("Choose the board for Kanban view {0}.").format(self.label))
		sharing_changed = self.is_new() and (self.is_shared or self.is_pinned)
		if not self.is_new():
			sharing_changed = self.has_value_changed("is_shared") or self.has_value_changed("is_pinned")
		if sharing_changed and not is_approver():
			frappe.throw(_("Only a Compliance Manager can share or pin a view."), frappe.PermissionError)
		if self.is_pinned and not self.is_shared:
			self.is_shared = 1
