// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Trademark", {
	refresh(frm) {
		if (frm.is_new() || !frm.has_perm("write")) {
			return;
		}
		frm.add_custom_button(__("Add Date"), () => {
			frappe.new_doc("Legal Date", {
				reference_doctype: "Trademark",
				reference_name: frm.doc.name,
			});
		});
	},
});
