from frappe import _


def get_data():
	return {
		"fieldname": "compliance_item",
		"transactions": [
			{"label": _("Renewals"), "items": ["Compliance Renewal"]},
			{"label": _("Reminders Sent"), "items": ["Compliance Reminder Log"]},
		],
	}
