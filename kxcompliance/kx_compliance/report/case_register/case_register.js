// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Case Register"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
		{
			fieldname: "case_type",
			label: __("Type"),
			fieldtype: "Select",
			options: [
				"",
				"Litigation",
				"Tax Notice or Assessment",
				"Labour",
				"Consumer",
				"Arbitration",
				"Regulatory",
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
				"Stayed",
				"Reserved for Order",
				"Disposed - In Our Favour",
				"Disposed - Against Us",
				"Settled",
				"Withdrawn",
			],
		},
		{
			fieldname: "risk",
			label: __("Risk"),
			fieldtype: "Select",
			options: ["", "Probable", "Possible", "Remote"],
		},
		{ fieldname: "responsible", label: __("Responsible"), fieldtype: "Link", options: "User" },
	],
};
