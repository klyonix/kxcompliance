// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Trademark Register"] = {
	filters: [
		{ fieldname: "applicant", label: __("Applicant"), fieldtype: "Link", options: "Company" },
		{ fieldname: "brand", label: __("Brand"), fieldtype: "Link", options: "Brand" },
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: [
				"",
				"New Application",
				"Formalities Check Pass",
				"Marked for Exam",
				"Objected",
				"Accepted and Advertised",
				"Opposed",
				"Registered",
				"Refused",
				"Abandoned",
				"Withdrawn",
				"Removed",
			],
		},
	],
};
