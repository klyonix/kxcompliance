# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""The app is now called KlyONIX Compliance. Sites still showing the old default name get the new
one; a name the site chose itself is kept. Safe to run again."""

import frappe

SETTINGS = "KX Compliance Settings"
OLD_DEFAULT = "Compliance Plus"


def execute():
	if frappe.db.get_single_value(SETTINGS, "app_name") == OLD_DEFAULT:
		frappe.db.set_single_value(SETTINGS, "app_name", "KlyONIX Compliance")
