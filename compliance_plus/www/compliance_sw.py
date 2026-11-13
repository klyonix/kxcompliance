# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Serve the app's service worker from the site root, so it can look after /compliance.

A worker only controls pages under its own folder, and the build writes it under
/assets, which does not hold /compliance; served here it can.
"""

import os

import frappe

base_template_path = "www/compliance_sw.js"
no_cache = 1


def get_context(context):
	path = frappe.get_app_path("compliance_plus", "public", "frontend", "sw.js")
	source = ""
	if os.path.exists(path):
		# A fixed path inside this app's build output; nothing in it comes from the request.
		with open(path) as handle:  # nosemgrep
			source = handle.read()
	return {"sw_source": source}
