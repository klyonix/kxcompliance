# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from kxcompliance import compat, scoped
from kxcompliance.kx_compliance.register import CLOSED_TASK_STATUSES
from kxcompliance.kx_compliance.statutory import extensions_for, find_extension


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
			enqueue_after_commit=not compat.in_test(),
			now=compat.in_test(),
		)


def apply_extension(extension: str):
	"""Move every open task this extension covers; filed tasks keep the dates they were filed against.

	Open tasks it moved before but no longer covers (its periods or obligation were changed) go
	back to their usual due date, or to another extension that covers them.
	"""
	doc = frappe.get_doc("Compliance Due Date Extension", extension)
	still_open = ("not in", CLOSED_TASK_STATUSES)
	covered = scoped.get_all(
		"Compliance Task",
		filters={
			"obligation_template": doc.obligation_template,
			"period_end": ("between", [doc.periods_ending_from, doc.periods_ending_to]),
			"status": still_open,
		},
		pluck="name",
	)
	for name in covered:
		move_task(name, doc.new_due_date, doc.name)

	left = scoped.get_all(
		"Compliance Task",
		filters={"extension": doc.name, "name": ("not in", covered or [""]), "status": still_open},
		fields=["name", "obligation_template", "period_end"],
	)
	others = [
		row for row in extensions_for([row.obligation_template for row in left]) if row.name != doc.name
	]
	for row in left:
		other = find_extension(others, row.obligation_template, getdate(row.period_end))
		move_task(row.name, other.new_due_date if other else None, other.name if other else None)


def move_task(name: str, extended_due_date, extension: str | None):
	task = frappe.get_doc("Compliance Task", name)
	task.extended_due_date = extended_due_date
	task.extension = extension
	task.flags.ignore_permissions = True  # applied by the system on a manager's extension
	task.save()
