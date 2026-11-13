// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Contingent Liabilities"] = {
	filters: [
		{
			fieldname: "as_at",
			label: __("As At"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
	],
};
