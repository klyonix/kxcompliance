// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Document Request", {
	refresh(frm) {
		if (frm.is_new() || !frm.perm[0]?.write) return;
		if (frm.doc.status === "Uploaded") {
			frm.add_custom_button(__("Accept"), () =>
				frm.call("accept").then(() => frm.reload_doc())
			);
			frm.add_custom_button(__("Send Back"), () =>
				frappe.prompt(
					{
						fieldname: "note",
						fieldtype: "Small Text",
						label: __("What is wrong"),
						reqd: 1,
					},
					({ note }) => frm.call("send_back", { note }).then(() => frm.reload_doc()),
					__("Send back to the client")
				)
			);
		}
		if (["Requested", "Uploaded"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Withdraw"), () =>
				frm.call("withdraw").then(() => frm.reload_doc())
			);
		}
	},
});
