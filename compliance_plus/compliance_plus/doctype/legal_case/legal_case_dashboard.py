from frappe import _


def get_data():
	return {
		"fieldname": "reference_name",
		"non_standard_fieldnames": {"Legal Case": "appeal_of"},
		"transactions": [
			{"label": _("Dates"), "items": ["Legal Date"]},
			{"label": _("Appeals"), "items": ["Legal Case"]},
		],
	}
