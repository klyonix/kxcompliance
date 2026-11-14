# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_first_day, nowdate

from compliance_plus.compliance_plus.statutory import generate_tasks


class CompanyComplianceProfile(Document):
	def validate(self):
		seen = set()
		for row in self.obligations:
			key = (row.obligation_template, row.registration_number or row.state or "")
			if key in seen:
				frappe.throw(
					_("Obligations row {0}: {1} is already listed for this registration.").format(
						row.idx, row.obligation_template
					)
				)
			seen.add(key)

	@frappe.whitelist(methods=["POST"])
	def find_obligations(self) -> int:
		self.check_permission("write")
		listed = {
			(row.obligation_template, row.registration_number or row.state or "") for row in self.obligations
		}
		added = 0
		for template_name in frappe.get_all(
			"Compliance Obligation Template",
			# Event templates are not standing obligations; recording the event makes their tasks.
			filters={"is_active": 1, "add_by_default": 1, "event_type": ("is", "not set")},
			pluck="name",
			order_by="law asc, template_name asc",
		):
			template = frappe.get_cached_doc("Compliance Obligation Template", template_name)
			if not template.applies_to(self.company_type):
				continue
			for registration in self.registrations_for(template):
				key = (
					template.name,
					registration.get("registration_number") or registration.get("state") or "",
				)
				if key in listed:
					continue
				self.append(
					"obligations",
					{
						"obligation_template": template.name,
						"registration_number": registration.get("registration_number"),
						"state": registration.get("state"),
						"responsible": self.default_responsible,
						"reviewer": self.default_reviewer,
						"start_from": get_first_day(nowdate()),
					},
				)
				listed.add(key)
				added += 1
		self.save()
		return added

	def registrations_for(self, template) -> list[dict]:
		states = template.state_list()
		if not template.registration_type:
			return [{}] if not states else []
		return [
			{"registration_number": row.registration_number, "state": row.state}
			for row in self.registrations
			if row.registration_type == template.registration_type and (not states or row.state in states)
		]

	@frappe.whitelist(methods=["POST"])
	def generate_tasks_now(self) -> int:
		self.check_permission("write")
		return generate_tasks(company=self.company)
