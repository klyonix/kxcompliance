# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from compliance_plus.compliance_plus.register import CLOSED_TASK_STATUSES


class ComplianceDueDateExtension(Document):
	def validate(self):
		if getdate(self.periods_ending_from) > getdate(self.periods_ending_to):
			frappe.throw(
				_("Periods Ending From ({0}) cannot be after Periods Ending To ({1}).").format(
					frappe.format(self.periods_ending_from, "Date"),
					frappe.format(self.periods_ending_to, "Date"),
				)
			)

	def on_update(self):
		frappe.enqueue(
			apply_extension,
			extension=self.name,
			queue="long",
			enqueue_after_commit=not frappe.in_test,
			now=frappe.in_test,
		)


def apply_extension(extension: str):
	"""Move every open task this extension covers; filed tasks keep the dates they were filed against."""
	doc = frappe.get_doc("Compliance Due Date Extension", extension)
	tasks = frappe.get_all(
		"Compliance Task",
		filters={
			"obligation_template": doc.obligation_template,
			"period_end": ("between", [doc.periods_ending_from, doc.periods_ending_to]),
			"status": ("not in", CLOSED_TASK_STATUSES),
		},
		pluck="name",
	)
	for name in tasks:
		task = frappe.get_doc("Compliance Task", name)
		task.extended_due_date = doc.new_due_date
		task.extension = doc.name
		task.flags.ignore_permissions = True  # applied by the system on a manager's extension
		task.save()
