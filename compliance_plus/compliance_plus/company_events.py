# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Company events, such as a director appointed or shares allotted, and the filing tasks each
one calls for: a template with an Event Type is due a set number of days after the event."""

import frappe
from frappe import _
from frappe.utils import add_days, formatdate, getdate

from compliance_plus.compliance_plus.statutory import extensions_for, find_extension


def event_templates(event_type: str, company_type: str) -> list:
	"""The active templates an event of this type calls for, for this kind of company."""
	templates = [
		frappe.get_cached_doc("Compliance Obligation Template", name)
		for name in frappe.get_all(
			"Compliance Obligation Template",
			filters={"is_active": 1, "event_type": event_type},
			pluck="name",
			order_by="template_name asc",
		)
	]
	return [template for template in templates if template.applies_to(company_type)]


def make_event_tasks(event) -> list[str]:
	"""Create the filing tasks for a newly recorded event; returns their names."""
	profile = frappe.get_doc("Company Compliance Profile", event.company)
	templates = event_templates(event.event_type, profile.company_type)
	if not templates:
		return []
	event_date = getdate(event.event_date)
	extensions = extensions_for([template.name for template in templates])
	made = []
	for template in templates:
		values = {
			"doctype": "Compliance Task",
			"obligation_template": template.name,
			"company": event.company,
			"company_event": event.name,
			"period_start": event_date,
			"period_end": event_date,
			"period_label": f"{_(event.event_type)}, {formatdate(event_date)}",
			"due_date": getdate(add_days(event_date, template.days_after_event)),
			"responsible": profile.default_responsible,
			"reviewer": profile.default_reviewer,
			"task_key": f"{template.name}|{event.company}|{event.name}",
		}
		extension = find_extension(extensions, template.name, event_date)
		if extension:
			values["extended_due_date"] = extension.new_due_date
			values["extension"] = extension.name
		task = frappe.get_doc(values)
		# Made by the app for the event; the person recording it may not hold these tasks.
		task.flags.ignore_permissions = True
		task.insert()
		made.append(task.name)
	return made
