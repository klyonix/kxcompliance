// Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Compliance Setup Import", {
	refresh(frm) {
		frm.set_intro(
			__("Bulk setup runs in the app: open Clients, then Import from a sheet."),
			"blue"
		);
	},
});
