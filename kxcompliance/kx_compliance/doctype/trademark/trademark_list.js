// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

const TRADEMARK_COLOURS = {
	Registered: "green",
	Objected: "red",
	Opposed: "red",
	"Accepted and Advertised": "blue",
	Refused: "gray",
	Abandoned: "gray",
	Withdrawn: "gray",
	Removed: "gray",
};

frappe.listview_settings["Trademark"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		return [
			__(doc.status),
			TRADEMARK_COLOURS[doc.status] || "orange",
			"status,=," + doc.status,
		];
	},
};
