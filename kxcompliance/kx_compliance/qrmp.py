# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""The fixed sum a QRMP company may pay by PMT-06.

For each of a quarter's first two months, a company in the QRMP scheme pays either the tax
actually due (self-assessment), or a fixed sum: 35% of the tax it paid in cash with the previous
quarter's GSTR-3B, or all of the tax paid in cash for the last month of that quarter if it then
filed monthly (CGST rule 61(1), proviso; Circular 143/13/2020-GST). The app works the fixed sum
out from the GSTR-3B recorded here, taking its Amount Paid as the tax paid in cash.
"""

from datetime import date

import frappe
from frappe.utils import add_days, flt, getdate

from kxcompliance import scoped

FIXED_SUM_FORM = "PMT-06"
RETURN_FORM = "GSTR-3B"
FILED_STATUSES = ("Filed", "Filed Late")
# The share of the previous period's cash tax, by how GSTR-3B was filed then.
SHARE = {"Quarterly": 35, "Monthly": 100}


def fixed_sum(task) -> dict | None:
	"""The fixed sum for a PMT-06 filing, and what it comes from; None for any other filing.

	`amount` is None when no filed GSTR-3B for the previous quarter is recorded.
	"""
	rules = frappe.get_cached_doc("Compliance Obligation Template", task.obligation_template)
	if rules.law != "GST" or rules.form != FIXED_SUM_FORM or not task.period_start:
		return None
	start = getdate(task.period_start)
	# Financial-year quarters begin in April, July, October and January, as calendar ones do.
	quarter_start = date(start.year, start.month - (start.month - 1) % 3, 1)
	previous_end = getdate(add_days(quarter_start, -1))
	returns = {
		row.name: row.frequency
		for row in scoped.get_all(
			"Compliance Obligation Template",
			filters={"law": "GST", "form": RETURN_FORM},
			fields=["name", "frequency"],
		)
	}
	filed = scoped.get_all(
		"Compliance Task",
		filters={
			"obligation_template": ("in", list(returns) or [""]),
			"company": task.company,
			"registration_number": task.registration_number or ("is", "not set"),
			"period_end": previous_end,
			"status": ("in", FILED_STATUSES),
		},
		fields=["name", "obligation_template", "period_label", "amount_paid"],
	)
	# A quarterly return for the previous quarter comes first; else the monthly one for its last month.
	filed.sort(key=lambda row: returns.get(row.obligation_template) != "Quarterly")
	quarter_label = f"{previous_end:%b %Y}"
	if not filed:
		return {"amount": None, "previous_period": quarter_label}
	basis = filed[0]
	percent = SHARE.get(returns.get(basis.obligation_template), 100)
	return {
		"amount": flt(flt(basis.amount_paid) * percent / 100, 0),
		"percent": percent,
		"paid": flt(basis.amount_paid, 2),
		"from_filing": basis.name,
		"from_label": f"{basis.obligation_template}, {basis.period_label}",
		"previous_period": quarter_label,
	}
