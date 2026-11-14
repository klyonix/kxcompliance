// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.views.calendar["Compliance Task"] = {
	field_map: {
		start: "effective_due_date",
		end: "effective_due_date",
		id: "name",
		title: "obligation_template",
		status: "status",
	},
	get_events_method: "frappe.desk.calendar.get_events",
};
