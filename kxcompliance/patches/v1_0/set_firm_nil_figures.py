import frappe
from frappe.utils import flt

from kxcompliance.kx_compliance.penalty_library import NIL_FIELDS, NIL_PENALTIES


def execute():
	"""A firm's own late-filing figures now include a late NIL return's (RK, 21 Nov 2026). Records
	kept before that have none, and would override the library's NIL figures with nothing, so they
	take the library's. Only records with no NIL figures at all are filled, so running it again
	never overwrites figures a firm has since set."""
	for row in frappe.get_all(
		"Compliance Penalty Figures", fields=["name", "obligation_template", *NIL_FIELDS]
	):
		if any(flt(row.get(field)) for field in NIL_FIELDS):
			continue
		figures = NIL_PENALTIES.get(row.obligation_template, {})
		if not figures:
			continue
		frappe.db.set_value(
			"Compliance Penalty Figures",
			row.name,
			{field: figures.get(field, 0) for field in NIL_FIELDS},
			update_modified=False,
		)
