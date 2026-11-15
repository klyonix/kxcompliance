# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

from kxcompliance.install import keep_client_role_off_desk


def execute():
	"""Sites installed with the client role given the Desk: its logins become Website Users again.
	Safe to run again: a role already off the Desk is left alone."""
	keep_client_role_off_desk()
