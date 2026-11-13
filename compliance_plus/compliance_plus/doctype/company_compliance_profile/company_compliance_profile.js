// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Company Compliance Profile", {
	refresh(frm) {
		if (frm.is_new() || !frm.has_perm("write")) {
			return;
		}
		frm.add_custom_button(__("Find Applicable Obligations"), () => {
			frm.call("find_obligations").then(({ message }) => {
				frappe.show_alert({
					message: __("{0} obligations added", [message]),
					indicator: "green",
				});
				frm.reload_doc();
			});
		});
		frm.add_custom_button(__("Make Tasks Now"), () => {
			frm.call("generate_tasks_now").then(({ message }) => {
				frappe.show_alert({
					message: __("{0} tasks made", [message]),
					indicator: "green",
				});
			});
		});
	},
});
