// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Compliance Event", {
	setup(frm) {
		// Offer only the events that call for a filing from this company's kind.
		frm.set_query("event_type", () => ({
			query: "compliance_plus.compliance_plus.company_events.event_type_query",
			filters: { company: frm.doc.company },
		}));
	},
	company(frm) {
		if (frm.is_new() && frm.doc.event_type) frm.set_value("event_type", null);
	},
});
