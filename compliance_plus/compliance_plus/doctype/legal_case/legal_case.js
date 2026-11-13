// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Legal Case", {
	refresh(frm) {
		if (frm.is_new() || !frm.has_perm("write")) {
			return;
		}
		frm.add_custom_button(__("Add Date"), () => {
			frappe.new_doc("Legal Date", {
				reference_doctype: "Legal Case",
				reference_name: frm.doc.name,
			});
		});
		frm.add_custom_button(__("File Appeal"), () => {
			frappe.new_doc("Legal Case", {
				appeal_of: frm.doc.name,
				title: __("Appeal: {0}", [frm.doc.title]),
				company: frm.doc.company,
				case_type: frm.doc.case_type,
				opposing_party: frm.doc.opposing_party,
				our_role: "Appellant",
			});
		});
	},
});
