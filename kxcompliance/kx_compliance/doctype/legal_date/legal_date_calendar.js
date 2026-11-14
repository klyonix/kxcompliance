// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.views.calendar["Legal Date"] = {
	field_map: {
		start: "date",
		end: "date",
		id: "name",
		title: "reference_title",
		status: "status",
	},
	get_events_method: "frappe.desk.calendar.get_events",
};
