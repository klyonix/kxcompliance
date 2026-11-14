// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

const COMPLIANCE_TASK_COLOURS = {
	Open: "orange",
	"In Progress": "blue",
	"Ready for Review": "purple",
	Filed: "green",
	"Filed Late": "yellow",
	"Not Applicable": "gray",
	Cancelled: "gray",
};

frappe.listview_settings["Compliance Task"] = {
	add_fields: ["status", "is_overdue"],
	get_indicator(doc) {
		if (doc.is_overdue) {
			return [__("Overdue"), "red", "is_overdue,=,1"];
		}
		return [
			__(doc.status),
			COMPLIANCE_TASK_COLOURS[doc.status] || "gray",
			"status,=," + doc.status,
		];
	},
};
