# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

from frappe import _


def get_data():
	"""A signatory's DSCs, which are register items held by the signatory."""
	return {
		"fieldname": "holder",
		"non_standard_fieldnames": {"Compliance Item": "holder"},
		"dynamic_links": {"holder": ["Signatory", "holder_type"]},
		"transactions": [{"label": _("Digital Signatures"), "items": ["Compliance Item"]}],
	}
