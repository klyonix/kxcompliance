// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Compliance Renewal", {
	setup(frm) {
		frm.set_query("compliance_item", () => ({ filters: { is_cancelled: 0 } }));
	},
});
