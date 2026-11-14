// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["On-time Filing"] = {
	filters: [
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: ["Company", "Client", "Law", "Responsible"],
			default: "Company",
		},
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
		{
			fieldname: "client",
			label: __("Client"),
			fieldtype: "Link",
			options: "Compliance Client",
		},
		{ fieldname: "from_date", label: __("Due From"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("Due To"), fieldtype: "Date" },
	],
};
