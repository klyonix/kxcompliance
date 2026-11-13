// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

const LEGAL_DATE_COLOURS = {
	Scheduled: "blue",
	Done: "green",
	Adjourned: "orange",
	Missed: "red",
	Cancelled: "gray",
};

frappe.listview_settings["Legal Date"] = {
	add_fields: ["status", "is_overdue"],
	get_indicator(doc) {
		if (doc.is_overdue) {
			return [__("Outcome Not Recorded"), "red", "is_overdue,=,1"];
		}
		return [
			__(doc.status),
			LEGAL_DATE_COLOURS[doc.status] || "gray",
			"status,=," + doc.status,
		];
	},
};
