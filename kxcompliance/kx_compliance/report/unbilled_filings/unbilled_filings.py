# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from kxcompliance.kx_compliance.billing import unbilled_for_clients


def execute(filters: dict | None = None):
	"""Returns filed for clients, with a price, that are on no bill yet."""
	filters = frappe._dict(filters or {})
	return get_columns(), unbilled_for_clients(filters.client)


def get_columns():
	return [
		{
			"label": _("Client"),
			"fieldname": "client",
			"fieldtype": "Link",
			"options": "Compliance Client",
			"width": 180,
		},
		{
			"label": _("Filing"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Compliance Task",
			"width": 130,
		},
		{"label": _("Return"), "fieldname": "obligation_template", "fieldtype": "Data", "width": 200},
		{"label": _("Period"), "fieldname": "period_label", "fieldtype": "Data", "width": 110},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 200,
		},
		{"label": _("Filed On"), "fieldname": "filed_on", "fieldtype": "Date", "width": 100},
		{"label": _("Fee"), "fieldname": "fee", "fieldtype": "Currency", "width": 110},
	]
