# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""The PWA manifest, with the app name and logo each site sets in Compliance Plus Settings."""

import json

import frappe

base_template_path = "www/compliance_manifest.json"
no_cache = 1

DEFAULT_ICON = "/assets/compliance_plus/frontend/icon-512.png"


def get_context(context):
	name = frappe.db.get_single_value("Compliance Plus Settings", "app_name") or "Compliance Plus"
	logo = frappe.db.get_single_value("Compliance Plus Settings", "app_logo") or DEFAULT_ICON
	manifest = {
		"name": name,
		"short_name": name,
		"start_url": "/compliance",
		"scope": "/compliance",
		"display": "standalone",
		"background_color": "#ffffff",
		"theme_color": "#ffffff",
		"icons": [
			{"src": logo, "sizes": "192x192", "purpose": "any"},
			{"src": logo, "sizes": "512x512", "purpose": "any"},
		],
	}
	return {"manifest": json.dumps(manifest)}
