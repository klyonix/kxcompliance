// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Compliance Item", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.is_cancelled || !frm.has_perm("write")) {
			return;
		}
		frm.add_custom_button(__("Start Renewal"), () => {
			frappe.new_doc("Compliance Renewal", { compliance_item: frm.doc.name });
		});
		frm.add_custom_button(__("Cancel Item"), () => {
			frappe.prompt(
				{
					fieldname: "reason",
					fieldtype: "Small Text",
					label: __("Reason"),
					reqd: 1,
				},
				({ reason }) => {
					frm.call("cancel_item", { reason }).then(() => frm.reload_doc());
				},
				__("Cancel {0}", [frm.doc.name]),
				__("Cancel Item")
			);
		});
	},

	holder_type(frm) {
		frm.set_value("holder", frm.doc.holder_type === "Company" ? frm.doc.company : null);
	},

	item_type(frm) {
		if (!frm.doc.item_type) {
			return;
		}
		frappe.db.get_doc("Compliance Item Type", frm.doc.item_type).then((type_doc) => {
			frm.clear_table("reminders");
			(type_doc.reminders || []).forEach((rule) => {
				frm.add_child("reminders", { days_before: rule.days_before });
			});
			frm.refresh_field("reminders");
		});
	},
});
