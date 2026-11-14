# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Onboarding is for new sites. A site that already has a company set up for compliance is
marked done (as an organisation) so its managers are not sent through it."""

import frappe

SETTINGS = "KX Compliance Settings"


def execute():
	if frappe.db.get_single_value(SETTINGS, "setup_complete"):
		return
	if not frappe.db.count("Company Compliance Profile"):
		return
	frappe.db.set_single_value(SETTINGS, {"setup_complete": 1, "account_type": "Organisation"})
