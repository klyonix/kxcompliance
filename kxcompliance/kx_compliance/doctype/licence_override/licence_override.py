# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from kxcompliance import scoped
from kxcompliance.kx_compliance.party_licences import DOCUMENTS, override_key


class LicenceOverride(Document):
	def validate(self):
		if self.reference_doctype not in DOCUMENTS:
			frappe.throw(_("Licences are not checked on {0}.").format(_(self.reference_doctype)))
		if not scoped.exists(self.reference_doctype, self.reference_name):
			frappe.throw(_("{0} {1} does not exist.").format(_(self.reference_doctype), self.reference_name))
		if not (self.reason or "").strip():
			frappe.throw(_("Give a reason for letting {0} through.").format(self.reference_name))
		self.override_key = override_key(self.reference_doctype, self.reference_name)
		self.approved_by = self.approved_by or frappe.session.user
