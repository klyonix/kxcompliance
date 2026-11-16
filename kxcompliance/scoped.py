# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Extension points for apps installed beside this one.

Frappe's permission hooks cover get_list, documents and the REST API, but not the reads this app
makes itself (get_all, get_value, exists, count, the query builder). Those reads go through this
module, so another app can narrow them, supply the settings, set limits and run the scheduled
jobs its own way. With no such app installed every function here does exactly what the Frappe
call it wraps does.

Hooks another app may declare in its hooks.py:

    kxcompliance_scope = "my_app.module.conditions"
        conditions(doctype: str) -> dict | None
        Extra conditions for every read of that doctype, as {fieldname: value} or
        {fieldname: (operator, value)}. Return nothing for a doctype that is not narrowed,
        and for Single doctypes.

    kxcompliance_settings = "my_app.module.settings"
        settings(for_update: bool) -> Document | None
        The KX Compliance Settings to use. for_update asks for a document that will be saved.

    kxcompliance_check_limit = "my_app.module.check_limit"
        check_limit(kind: str, **context) -> None
        Called before a company, staff user or client is added (kind "Company", "User" or
        "Compliance Client"); throws to refuse.

    kxcompliance_run_job = "my_app.module.run_job"
        run_job(job: Callable[[], None]) -> bool
        Called by each scheduled job with the module-level function that does the work.
        Return True once the hook has run or queued it; otherwise the job runs here.
"""

from collections.abc import Callable

import frappe
from pypika.terms import Criterion

SETTINGS = "KX Compliance Settings"


def conditions(doctype: str) -> dict:
	extra = {}
	for path in frappe.get_hooks("kxcompliance_scope"):
		extra.update(frappe.get_attr(path)(doctype) or {})
	return extra


def filters(doctype: str, given=None):
	"""The given filters (None, a name, a dict or a list) with the doctype's extra conditions."""
	extra = conditions(doctype)
	if not extra:
		return given
	return merge(given, extra)


def merge(given, extra: dict):
	if given is None:
		return dict(extra)
	if isinstance(given, str | int):
		return {"name": given, **extra}
	if isinstance(given, dict):
		return {**given, **extra}
	rows = list(given)
	if rows and isinstance(rows[0], str):
		rows = [rows]
	for fieldname, value in extra.items():
		operator, value = value if isinstance(value, tuple) else ("=", value)
		rows.append([fieldname, operator, value])
	return rows


def get_all(doctype: str, **kwargs) -> list:
	extra = conditions(doctype)
	if extra:
		kwargs["filters"] = merge(kwargs.get("filters"), extra)
	return frappe.get_all(doctype, **kwargs)


def get_value(doctype: str, given=None, fieldname="name", **kwargs):
	return frappe.db.get_value(doctype, filters(doctype, given), fieldname, **kwargs)


def get_cached_value(doctype: str, name: str, fieldname, **kwargs):
	if conditions(doctype):
		return get_value(doctype, name, fieldname, **kwargs)
	return frappe.get_cached_value(doctype, name, fieldname, **kwargs)


def exists(doctype: str, given=None, **kwargs):
	return frappe.db.exists(doctype, filters(doctype, given), **kwargs)


def count(doctype: str, given=None, **kwargs) -> int:
	return frappe.db.count(doctype, filters(doctype, given), **kwargs)


def get_query(doctype: str, **kwargs):
	extra = conditions(doctype)
	if extra:
		kwargs["filters"] = merge(kwargs.get("filters"), extra)
	return frappe.qb.get_query(doctype, **kwargs)


def where(table) -> Criterion:
	"""The extra conditions for a query-builder table; adds nothing when there are none.

	Use on every table of a query: .where(scoped.where(item)), or & scoped.where(item) in a join.
	"""
	doctype = table._table_name.removeprefix("tab")
	terms = []
	for fieldname, value in conditions(doctype).items():
		operator, value = value if isinstance(value, tuple) else ("=", value)
		terms.append(term(table[fieldname], operator, value))
	return Criterion.all(terms)


def term(field, operator: str, value):
	if operator == "=":
		return field == value
	if operator == "in":
		return field.isin(value)
	if operator == "is":
		return field.isnull() if value == "not set" else field.isnotnull()
	raise ValueError(f"kxcompliance_scope: operator {operator!r} is not supported")


def settings(for_update: bool = False):
	for path in frappe.get_hooks("kxcompliance_settings"):
		doc = frappe.get_attr(path)(for_update=for_update)
		if doc is not None:
			return doc
	return frappe.get_doc(SETTINGS) if for_update else frappe.get_cached_doc(SETTINGS)


def check_limit(kind: str, **context):
	for path in frappe.get_hooks("kxcompliance_check_limit"):
		frappe.get_attr(path)(kind, **context)


def run_job(job: Callable[[], None]):
	for path in frappe.get_hooks("kxcompliance_run_job"):
		if frappe.get_attr(path)(job):
			return
	job()
