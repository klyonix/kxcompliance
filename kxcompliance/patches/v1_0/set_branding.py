# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

from kxcompliance.install import set_branding


def execute():
	"""Sites installed before the app was the default: land in it after sign-in, with its logo,
	unless the site chose its own."""
	set_branding()
