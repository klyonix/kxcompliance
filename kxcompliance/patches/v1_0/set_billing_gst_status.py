# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""A firm set up to bill before GST status was asked for was set up charging GST: it is Registered.
A new field on a Single doctype takes no default on existing sites, so it is set here. Safe to run
again: only an empty status is filled in."""

import frappe


def execute():
	if not frappe.db.get_single_value("KX Compliance Settings", "gst_status"):
		frappe.db.set_single_value("KX Compliance Settings", "gst_status", "Registered")
