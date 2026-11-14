// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

const COMPLIANCE_ITEM_COLOURS = {
	Draft: "gray",
	Active: "green",
	"Due for Renewal": "orange",
	"Renewal in Progress": "blue",
	Expired: "red",
	Lapsed: "red",
	Cancelled: "gray",
};

frappe.listview_settings["Compliance Item"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		return [
			__(doc.status),
			COMPLIANCE_ITEM_COLOURS[doc.status] || "gray",
			"status,=," + doc.status,
		];
	},
};
