// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Compliance Calendar"] = {
	filters: [
		{
			fieldname: "month",
			label: __("Any Day in the Month"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
		{
			fieldname: "law",
			label: __("Law"),
			fieldtype: "Select",
			options: [
				"",
				"GST",
				"Income Tax",
				"TDS/TCS",
				"PF",
				"ESI",
				"Professional Tax",
				"Labour Welfare Fund",
				"Companies Act",
				"LLP Act",
				"Other",
			],
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: [
				"",
				"Open",
				"In Progress",
				"Ready for Review",
				"Filed",
				"Filed Late",
				"Not Applicable",
				"Cancelled",
			],
		},
		{ fieldname: "responsible", label: __("Responsible"), fieldtype: "Link", options: "User" },
	],
};
