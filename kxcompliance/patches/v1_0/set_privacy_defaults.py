import frappe
from frappe.utils import cint


def execute():
	"""New defaults on KX Compliance Settings, which a Single does not take by itself."""
	settings = frappe.get_single("KX Compliance Settings")
	values = {}
	if not cint(settings.notice_version):
		values["notice_version"] = 1
	if not cint(settings.reminder_log_days):
		values["reminder_log_days"] = 365
	for field, value in values.items():
		frappe.db.set_single_value("KX Compliance Settings", field, value)
