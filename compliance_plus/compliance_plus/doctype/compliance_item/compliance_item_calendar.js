// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.views.calendar["Compliance Item"] = {
	field_map: {
		start: "valid_until",
		end: "valid_until",
		id: "name",
		title: "title",
		status: "status",
	},
	get_events_method: "frappe.desk.calendar.get_events",
};
