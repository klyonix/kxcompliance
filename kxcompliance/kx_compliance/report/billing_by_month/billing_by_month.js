// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

// The financial year as set up in ERPNext, which is where the report starts.
const financial_year = () =>
	erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true) || [];

frappe.query_reports["Billing by Month"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("Billed From"),
			fieldtype: "Date",
			default: financial_year()[1],
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("Billed To"),
			fieldtype: "Date",
			default: financial_year()[2],
			reqd: 1,
		},
		{
			fieldname: "client",
			label: __("Client"),
			fieldtype: "Link",
			options: "Compliance Client",
		},
	],
};
