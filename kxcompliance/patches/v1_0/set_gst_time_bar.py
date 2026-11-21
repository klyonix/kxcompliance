import frappe
from frappe.utils import add_years, getdate, nowdate

from kxcompliance.kx_compliance.doctype.compliance_task.compliance_task import is_time_barred
from kxcompliance.kx_compliance.obligation_library import LIBRARY


def execute():
	"""Set the last day to file on existing filings of returns with a time-bar, and flag the open
	ones already past it (RK, 21 Nov 2026).

	The library's figures are read from the code, since the standard templates are brought up to
	date only after patches run. Only these two derived fields are written, so old filings are not
	validated again here. Safe to run again: it works them out afresh.
	"""
	years = {values["template_name"]: values["time_bar_years"] for values in LIBRARY}
	for row in frappe.get_all(
		"Compliance Obligation Template",
		filters={"time_bar_years": (">", 0)},
		fields=["name", "time_bar_years"],
	):
		years.setdefault(row.name, row.time_bar_years)
	years = {name: count for name, count in years.items() if count}
	if not years:
		return
	today = getdate(nowdate())
	for task in frappe.get_all(
		"Compliance Task",
		filters={"obligation_template": ("in", list(years))},
		fields=["name", "obligation_template", "effective_due_date", "status", "filed_on"],
	):
		if not task.effective_due_date:
			continue
		last_day = getdate(add_years(task.effective_due_date, years[task.obligation_template]))
		barred = is_time_barred(last_day, task.status, task.filed_on, today)
		frappe.db.set_value(
			"Compliance Task",
			task.name,
			{"last_filing_date": last_day, "is_time_barred": int(barred)},
			update_modified=False,
		)
