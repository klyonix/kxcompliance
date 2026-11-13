// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Compliance Register"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
		{ fieldname: "branch", label: __("Branch"), fieldtype: "Link", options: "Branch" },
		{ fieldname: "state", label: __("State"), fieldtype: "Data" },
		{
			fieldname: "item_type",
			label: __("Type"),
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
		{ fieldname: "responsible", label: __("Responsible"), fieldtype: "Link", options: "User" },
	],
};
