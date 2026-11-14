# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Trademark deadlines read "From Examination Report Received On on 10-11-2026": the field's
label already ends in "On". Reword the ones already made as "<label>: <date>", as new ones are.
Running it again changes nothing, since the new wording does not start with "From ".
"""

import re

import frappe

OLD_WORDING = re.compile(r"^From (?P<label>.+) on (?P<date>\S+)$")


def execute():
	legal_date = frappe.qb.DocType("Legal Date")
	rows = (
		frappe.qb.from_(legal_date)
		.select(legal_date.name, legal_date.purpose)
		.where((legal_date.reference_doctype == "Trademark") & (legal_date.purpose.like("From % on %")))
	).run(as_dict=True)
	for row in rows:
		match = OLD_WORDING.match(row.purpose or "")
		if match:
			frappe.db.set_value(
				"Legal Date",
				row.name,
				"purpose",
				f"{match['label']}: {match['date']}",
				update_modified=False,
			)
