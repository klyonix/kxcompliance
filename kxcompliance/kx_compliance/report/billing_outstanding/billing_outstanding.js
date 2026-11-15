// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Billing Outstanding"] = {
	filters: [
		{
			fieldname: "client",
			label: __("Client"),
			fieldtype: "Link",
			options: "Compliance Client",
		},
	],
};
