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

    kxcompliance_boot = "my_app.module.boot"
        boot() -> dict | None
        Notices shown at the top of the app, as {"notices": [{"text", "theme", "link_label",
        "link_url"}]}, and links on the Account page, as {"account_links": [{"label", "url",
        "icon"}]}. Each app's are added to the others'.

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
	"""Both the given filters and the extra conditions apply, also when they name the same field."""
	if given is None:
		return dict(extra)
	if isinstance(given, str | int):
		given = {"name": given}
	if isinstance(given, dict):
		if not set(given) & set(extra):
			return {**given, **extra}
		rows = [as_row(fieldname, value) for fieldname, value in given.items()]
	else:
		rows = list(given)
		if rows and isinstance(rows[0], str):
			rows = [rows]
	return rows + [as_row(fieldname, value) for fieldname, value in extra.items()]


def as_row(fieldname: str, value) -> list:
	"""A dict filter's entry as a list filter: {"status": "Open"} or {"status": ("in", [...])}."""
	if isinstance(value, list | tuple) and len(value) == 2 and isinstance(value[0], str):
		return [fieldname, value[0], value[1]]
	return [fieldname, "=", value]


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


def settings_record() -> dict:
	"""Which record holds the settings, for attaching a file such as a logo to it."""
	doc = settings()
	return {"doctype": doc.doctype, "name": doc.name or doc.doctype}


def check_limit(kind: str, **context):
	for path in frappe.get_hooks("kxcompliance_check_limit"):
		frappe.get_attr(path)(kind, **context)


def boot_extras() -> dict:
	"""The notices and Account links other apps add to the app (kxcompliance_boot)."""
	extras = {"notices": [], "account_links": []}
	for path in frappe.get_hooks("kxcompliance_boot"):
		given = frappe.get_attr(path)() or {}
		for key in extras:
			extras[key].extend(given.get(key) or [])
	return extras


def run_job(job: Callable[[], None]):
	for path in frappe.get_hooks("kxcompliance_run_job"):
		if frappe.get_attr(path)(job):
			return
	job()
