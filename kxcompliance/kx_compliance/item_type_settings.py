# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""A firm's own settings for an item type it may not change, such as one shared with other firms.

Someone who may change a type changes the type itself, as on a site of one firm. Where the type
is shared, the firm keeps its own settings in a Compliance Item Type Settings record, used instead
of the type's: whether it is in use, how its items renew, how long they still count after expiry,
whether a certificate is needed, and when new items are reminded. Going back to the shared
settings removes the record.
"""

import frappe
from frappe import _
from frappe.utils import cint

from kxcompliance import scoped

DOCTYPE = "Compliance Item Type Settings"
TYPE = "Compliance Item Type"
FIELDS = ("is_active", "renewal_cycle_months", "grace_days", "requires_document")
LIST_FIELDS = ("name", "category", *FIELDS)


def firm_settings(item_types) -> dict[str, frappe._dict]:
	"""The firm's own settings, by item type, for those it has set them for."""
	item_types = sorted({name for name in item_types if name})
	if not item_types:
		return {}
	rows = scoped.get_all(
		DOCTYPE, filters={"item_type": ("in", item_types)}, fields=["name", "item_type", *FIELDS]
	)
	return {row.item_type: row for row in rows}


def as_used(rows: list) -> list:
	"""The rows of Compliance Item Type as the firm uses them: its own settings over each type's."""
	own = firm_settings(row.name for row in rows)
	for row in rows:
		row.set_by_firm = row.name in own
		if row.set_by_firm:
			row.update({field: own[row.name][field] for field in FIELDS if field in row})
	return rows


def types_in_use() -> list[str]:
	"""The item types the firm uses, by name: those the person may read that are on for the firm."""
	rows = frappe.get_list(TYPE, fields=["name", "is_active"], order_by="name asc", limit=1000)
	return [row.name for row in as_used(rows) if row.is_active]


def overview() -> list[dict]:
	"""Every item type the person may read, as the firm uses it, for the types list."""
	rows = frappe.get_list(TYPE, fields=list(LIST_FIELDS), order_by="name asc", limit=1000)
	return as_used(rows)


def reminder_days(item_type: str) -> list[int]:
	"""The days before expiry a new item of this type is reminded, as the firm has them."""
	own = firm_settings([item_type]).get(item_type)
	parent = (DOCTYPE, own.name) if own else (TYPE, item_type)
	return scoped.get_all(
		"Compliance Reminder Rule",
		filters={"parenttype": parent[0], "parent": parent[1]},
		pluck="days_before",
		order_by="idx asc",
	)


def settings_of(item_type: str) -> dict:
	"""What the type screen shows: the settings in use, whether they are the firm's own, and
	whether this person may change the type itself."""
	doc = frappe.get_doc(TYPE, item_type)
	doc.check_permission("read")
	own = firm_settings([item_type]).get(item_type)
	source = own or doc
	return {
		"values": {field: source.get(field) for field in FIELDS},
		"reminders": reminder_days(item_type),
		"set_by_firm": bool(own),
		"may_edit_type": bool(frappe.has_permission(TYPE, "write", doc=doc)),
	}


def save_settings(item_type: str, values: dict, reminders: list) -> dict:
	"""Keep the firm's own settings for a type it may not change."""
	if not isinstance(values, dict) or set(values) - set(FIELDS):
		frappe.throw(_("Only these can be set for a shared type: {0}.").format(", ".join(FIELDS)))
	if not isinstance(reminders, list):
		frappe.throw(_("Reminders are a list of days before expiry."))
	name = firm_settings([item_type]).get(item_type, {}).get("name")
	doc = frappe.get_doc(DOCTYPE, name) if name else frappe.new_doc(DOCTYPE)
	doc.item_type = item_type
	for field in FIELDS:
		doc.set(field, cint(values.get(field)))
	doc.set("reminders", [{"days_before": cint(days)} for days in reminders])
	doc.save()
	return settings_of(item_type)


def use_shared_settings(item_type: str) -> dict:
	"""Back to the type's own settings: the firm's are removed."""
	name = firm_settings([item_type]).get(item_type, {}).get("name")
	if name:
		frappe.delete_doc(DOCTYPE, name)
	return settings_of(item_type)
