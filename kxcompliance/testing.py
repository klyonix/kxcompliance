# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""The test base classes on Frappe 16, and their Frappe 15 equivalent, for the app's tests."""

from contextlib import contextmanager

import frappe

try:
	from frappe.tests import IntegrationTestCase, UnitTestCase
except ImportError:  # Frappe 15: one class, with the same set_user and freeze_time
	from frappe.tests.utils import FrappeTestCase as IntegrationTestCase
	from frappe.tests.utils import FrappeTestCase as UnitTestCase

__all__ = ["IntegrationTestCase", "UnitTestCase", "as_user"]


@contextmanager
def as_user(user: str):
	"""Act as someone outside a test case's own methods (set_user is not a class method on 15)."""
	old = frappe.session.user
	frappe.set_user(user)
	try:
		yield
	finally:
		frappe.set_user(old)
