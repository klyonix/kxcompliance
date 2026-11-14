# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Client logins need the Compliance Client role before the doctypes that grant it are synced."""

from compliance_plus.install import CLIENT_ROLE, create_role


def execute():
	create_role(CLIENT_ROLE, desk_access=0)
