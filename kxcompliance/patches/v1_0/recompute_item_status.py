import frappe
from frappe.utils import nowdate

from kxcompliance.kx_compliance.register import (
	compute_status,
	due_soon_days,
	get_type_rules,
	is_certificate_missing,
	open_renewal_statuses,
)


def execute():
	"""Draft is no longer a status: work out every item's status by its dates and open renewal,
	and flag the ones whose certificate is missing (RK, 15 Nov 2026).

	Only these two derived fields are written, so old records are not validated again here.
	"""
	items = frappe.get_all(
		"Compliance Item",
		fields=["name", "item_type", "status", "is_cancelled", "valid_until", "certificate"],
	)
	rules = get_type_rules([item.item_type for item in items])
	renewals = open_renewal_statuses([item.name for item in items])
	today = nowdate()
	soon = due_soon_days()
	for item in items:
		type_rules = rules.get(item.item_type) or frappe._dict()
		status = compute_status(
			is_cancelled=bool(item.is_cancelled),
			valid_until=item.valid_until,
			renewal_status=renewals.get(item.name),
			grace_days=type_rules.grace_days or 0,
			today=today,
			soon_days=soon,
		)
		missing = is_certificate_missing(
			requires_document=bool(type_rules.requires_document),
			has_certificate=bool(item.certificate),
			is_cancelled=bool(item.is_cancelled),
		)
		frappe.db.set_value(
			"Compliance Item",
			item.name,
			{"status": status, "certificate_missing": int(missing)},
			update_modified=False,
		)
