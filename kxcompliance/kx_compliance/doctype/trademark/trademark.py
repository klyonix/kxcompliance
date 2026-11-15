# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months, getdate

from kxcompliance.kx_compliance.legal import (
	ENDED_MARK_STATUSES,
	MARK_STATUS_FIELDS,
	cancel_scheduled_dates,
	check_status_change,
	pass_company_to_dates,
	pass_people_to_dates,
)
from kxcompliance.kx_compliance.register import check_reassignment

# A date entered on the trademark, the deadline it starts, and how long that deadline runs.
DEADLINES = (
	("examination_report_on", "Examination Report Reply", 0, 30),
	("journal_date", "Opposition Window", 4, 0),
	("opposition_notice_on", "Counter-Statement", 2, 0),
)
VALIDITY_MONTHS = 120
RENEWAL_ITEM_TYPE = "Trademark Registration"


class Trademark(Document):
	def validate(self):
		check_reassignment(self)
		check_status_change(self)
		self.validate_classes()
		if not self.renewal_item and self.filing_date:
			self.valid_until = add_months(self.filing_date, VALIDITY_MONTHS)
		if self.status == "Registered" and not self.flags.moving:
			missing = [
				_(self.meta.get_label(fieldname))
				for fieldname in ("registration_number", "registration_date")
				if not self.get(fieldname)
			]
			if missing:
				frappe.throw(
					_("Fill in {0} before marking {1} Registered.").format(", ".join(missing), self.mark)
				)

	def validate_classes(self):
		seen = set()
		for row in self.classes:
			if not 1 <= (row.class_number or 0) <= 45:
				frappe.throw(
					_("Classes row {0}: a class is between 1 and 45, not {1}.").format(
						row.idx, row.class_number
					)
				)
			if row.class_number in seen:
				frappe.throw(
					_("Classes row {0}: class {1} is listed twice.").format(row.idx, row.class_number)
				)
			seen.add(row.class_number)

	def on_update(self):
		if self.has_value_changed("applicant"):
			pass_company_to_dates(self.doctype, self.name, self.applicant)
		if self.has_value_changed("responsible") or self.has_value_changed("reviewer"):
			pass_people_to_dates(self.doctype, self.name, self.responsible, self.reviewer)
		for event_field, kind, months, days in DEADLINES:
			if self.get(event_field) and self.has_value_changed(event_field):
				self.set_deadline(
					event_field, kind, add_days(add_months(self.get(event_field), months), days)
				)
		if self.status == "Registered" and not self.renewal_item:
			self.make_renewal_item()
		if self.status in ENDED_MARK_STATUSES and self.has_value_changed("status"):
			cancel_scheduled_dates(
				self.doctype, self.name, _("Cancelled: the trademark was marked {0}.").format(_(self.status))
			)

	@frappe.whitelist(methods=["POST"])
	def change_status(self, status: str, details: dict | None = None):
		"""Move the mark to its next stage, with what the registry sent for it (MARK_STATUS_FIELDS)."""
		self.check_permission("write")
		if status not in self.meta.get_field("status").options.split("\n"):
			frappe.throw(_("{0} is not a status a trademark can have.").format(status))
		if status == self.status:
			frappe.throw(_("{0} is already {1}.").format(self.mark, _(status)))
		allowed = MARK_STATUS_FIELDS.get(status, ())
		extra = sorted(set(details or {}) - set(allowed))
		if extra:
			frappe.throw(
				_("{0} cannot be set when marking {1} {2}.").format(", ".join(extra), self.mark, _(status))
			)
		for fieldname, value in (details or {}).items():
			if not isinstance(value, str | type(None)):
				frappe.throw(_("{0} must be a single value.").format(_(self.meta.get_label(fieldname))))
			if value:
				self.set(fieldname, value)
		self.status = status
		self.save()

	def set_deadline(self, event_field: str, kind: str, due):
		existing = frappe.db.get_value(
			"Legal Date",
			{
				"reference_doctype": self.doctype,
				"reference_name": self.name,
				"kind": kind,
				"status": "Scheduled",
			},
		)
		legal_date = (
			frappe.get_doc("Legal Date", existing)
			if existing
			else frappe.new_doc(
				"Legal Date", reference_doctype=self.doctype, reference_name=self.name, kind=kind
			)
		)
		legal_date.date = due
		# "Examination Report Received On: 10-11-2026"; the field's label already says when.
		legal_date.purpose = _("{0}: {1}").format(
			_(self.meta.get_label(event_field)), frappe.format(self.get(event_field), "Date")
		)
		legal_date.save()

	def make_renewal_item(self):
		ensure_renewal_item_type()
		classes = ", ".join(str(row.class_number) for row in self.classes)
		item = frappe.get_doc(
			{
				"doctype": "Compliance Item",
				"title": _("Trademark {0} (class {1})").format(self.mark, classes),
				"item_type": RENEWAL_ITEM_TYPE,
				"company": self.applicant,
				"reference_number": self.registration_number or self.application_number,
				"issuing_authority": _("Trade Marks Registry"),
				"supplier": self.agent,
				"issue_date": self.registration_date,
				"valid_from": self.filing_date,
				"valid_until": self.valid_until,
				"certificate": self.registration_certificate,
				"responsible": self.responsible,
				"reviewer": self.reviewer,
			}
		)
		item.flags.ignore_permissions = True  # the register's copy of this trademark, made on registration
		item.insert()
		self.db_set("renewal_item", item.name)


def ensure_renewal_item_type():
	if frappe.db.exists("Compliance Item Type", RENEWAL_ITEM_TYPE):
		return
	frappe.get_doc(
		{
			"doctype": "Compliance Item Type",
			"type_name": RENEWAL_ITEM_TYPE,
			"category": "Registration",
			"renewal_cycle_months": VALIDITY_MONTHS,
			"reminders": [{"days_before": days} for days in (180, 90, 30)],
		}
	).insert(ignore_permissions=True)  # created the first time a trademark is registered


def follow_renewal(item):
	"""A renewed registration moves the trademark's Valid Until with it."""
	trademark = frappe.qb.DocType("Trademark")
	(
		frappe.qb.update(trademark)
		.set(trademark.valid_until, item.valid_until)
		.where(trademark.renewal_item == item.name)
	).run()
