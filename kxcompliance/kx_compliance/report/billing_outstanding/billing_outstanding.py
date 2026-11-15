# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate

from kxcompliance.kx_compliance.billing import AGEING, outstanding_by_client


def late_labels() -> dict[str, str]:
	"""Column labels, translated for whoever runs the report (not once, when the module loads)."""
	return {
		"not_due": _("Not Yet Due"),
		"late_30": _("1-30 Days Late"),
		"late_60": _("31-60 Days Late"),
		"late_90": _("61-90 Days Late"),
		"late_more": _("Over 90 Days Late"),
	}


def execute(filters: dict | None = None):
	"""What each client still owes the firm on its sent bills, by how late it is, most overdue first."""
	filters = frappe._dict(filters or {})
	return get_columns(), outstanding_by_client(filters.client, nowdate())


def get_columns():
	labels = late_labels()
	return [
		{
			"label": _("Client"),
			"fieldname": "client",
			"fieldtype": "Link",
			"options": "Compliance Client",
			"width": 200,
		},
		{"label": _("Bills"), "fieldname": "bills", "fieldtype": "Int", "width": 70},
		{"label": _("Still Due"), "fieldname": "outstanding", "fieldtype": "Currency", "width": 120},
		*[
			{"label": labels[key], "fieldname": key, "fieldtype": "Currency", "width": 120}
			for key, _low, _high in AGEING
		],
		{"label": _("Oldest Due Date"), "fieldname": "oldest_due", "fieldtype": "Date", "width": 110},
	]
