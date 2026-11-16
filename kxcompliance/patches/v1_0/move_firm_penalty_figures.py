"""Figures a firm set on a standard obligation move to its own Compliance Penalty Figures.

They used to be written on the obligation, marked Set by Us. The obligation now keeps the
library's figures (the next library update writes them back) and the firm's own are kept apart.
"""

import frappe

FIELDS = (
	"late_fee_per_day",
	"late_fee_flat",
	"late_fee_cap",
	"cap_at_tax",
	"interest_percent",
	"penalty_rule",
)


def execute():
	if not frappe.db.has_column("Compliance Obligation Template", "penalty_set_by_firm"):
		return
	template = frappe.qb.DocType("Compliance Obligation Template")
	rows = (
		frappe.qb.from_(template)
		.select(template.name, *(template[field] for field in FIELDS))
		.where((template.is_standard == 1) & (template.penalty_set_by_firm == 1))
	).run(as_dict=True)
	moved = set(frappe.get_all("Compliance Penalty Figures", pluck="obligation_template"))
	for row in rows:
		if row.name in moved:
			continue
		doc = frappe.get_doc(
			{"doctype": "Compliance Penalty Figures", "obligation_template": row.name}
			| {field: row[field] for field in FIELDS}
		)
		doc.flags.ignore_permissions = True  # a data move run by migrate, not by a person
		doc.insert()
	(
		frappe.qb.update(template)
		.set(template.penalty_set_by_firm, 0)
		.where(template.penalty_set_by_firm == 1)
	).run()
