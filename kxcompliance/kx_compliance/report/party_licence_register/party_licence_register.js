// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Party Licence Register"] = {
	filters: [
		{
			fieldname: "holder_type",
			label: __("Held By"),
			fieldtype: "Select",
			options: ["", "Customer", "Supplier"],
		},
		{
			fieldname: "item_type",
			label: __("Licence"),
			fieldtype: "Link",
			options: "Compliance Item Type",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: [
				"",
				"Draft",
				"Active",
				"Due for Renewal",
				"Renewal in Progress",
				"Expired",
				"Lapsed",
				"Cancelled",
			],
		},
	],
};
