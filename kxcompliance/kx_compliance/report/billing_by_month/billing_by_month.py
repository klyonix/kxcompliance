# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from kxcompliance.kx_compliance.billing import billing_by_month
from kxcompliance.kx_compliance.client_reports import financial_year


def execute(filters: dict | None = None):
	"""The firm's sent bills month by month: how many, before GST, GST, total, settled, still due,
	and the credit notes made."""
	filters = frappe._dict(filters or {})
	if not (filters.from_date and filters.to_date):
		filters.from_date, filters.to_date = financial_year()
	return get_columns(), billing_by_month(filters.from_date, filters.to_date, filters.client)


def get_columns():
	return [
		{"label": _("Month"), "fieldname": "month_name", "fieldtype": "Data", "width": 110},
		{"label": _("Bills"), "fieldname": "bills", "fieldtype": "Int", "width": 70},
		{"label": _("Before GST"), "fieldname": "before_gst", "fieldtype": "Currency", "width": 130},
		{"label": _("GST"), "fieldname": "gst", "fieldtype": "Currency", "width": 120},
		{"label": _("Total"), "fieldname": "total", "fieldtype": "Currency", "width": 130},
		{"label": _("Settled"), "fieldname": "settled", "fieldtype": "Currency", "width": 130},
		{"label": _("Still Due"), "fieldname": "still_due", "fieldtype": "Currency", "width": 130},
		{"label": _("Credit Notes"), "fieldname": "credited", "fieldtype": "Currency", "width": 130},
	]
