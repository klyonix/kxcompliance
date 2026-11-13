from frappe import _


def get_data():
	return {
		"fieldname": "compliance_task",
		"transactions": [{"label": _("Reminders Sent"), "items": ["Compliance Reminder Log"]}],
	}
