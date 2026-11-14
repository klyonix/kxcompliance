// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Legal Calendar"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), 30),
			reqd: 1,
		},
		{
			fieldname: "reference_doctype",
			label: __("For"),
			fieldtype: "Select",
			options: ["", "Legal Case", "Trademark"],
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: ["", "Scheduled", "Done", "Adjourned", "Missed", "Cancelled"],
		},
		{ fieldname: "responsible", label: __("Responsible"), fieldtype: "Link", options: "User" },
	],
};
