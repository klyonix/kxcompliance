# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""A firm's own late-filing figures for standard obligations.

A standard obligation's figures come from the library and change with its updates. A firm that
reckons differently keeps its own in a Compliance Penalty Figures record, used instead of the
library's; the obligation itself is left as the library made it. Going back to the library's
figures removes the record.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt

from kxcompliance import scoped
from kxcompliance.kx_compliance.penalty_library import FIELDS

DOCTYPE = "Compliance Penalty Figures"
TEMPLATE = "Compliance Obligation Template"


def firm_figures(templates) -> dict[str, frappe._dict]:
	"""The firm's own figures, by obligation, for those it has set them for."""
	templates = sorted({name for name in templates if name})
	if not templates:
		return {}
	rows = scoped.get_all(
		DOCTYPE,
		filters={"obligation_template": ("in", templates)},
		fields=["name", "obligation_template", *FIELDS],
	)
	return {row.obligation_template: row for row in rows}


def figures_of(template: str) -> dict:
	"""What the obligation screen shows: the figures in use, whether they are the firm's own, and
	whether this person may change the obligation itself (its In Use switch)."""
	doc = frappe.get_doc(TEMPLATE, template)
	doc.check_permission("read")
	own = firm_figures([template]).get(template)
	source = own or doc
	return {
		"figures": {field: source.get(field) for field in FIELDS},
		"set_by_firm": bool(own),
		"may_edit_obligation": bool(frappe.has_permission(TEMPLATE, "write", doc=doc)),
	}


def save_figures(template: str, figures: dict) -> dict:
	"""Keep the firm's own figures for a standard obligation."""
	if not isinstance(figures, dict) or set(figures) - set(FIELDS):
		frappe.throw(_("Only the late-filing figures can be set: {0}.").format(", ".join(FIELDS)))
	name = firm_figures([template]).get(template, {}).get("name")
	doc = frappe.get_doc(DOCTYPE, name) if name else frappe.new_doc(DOCTYPE)
	doc.obligation_template = template
	for field in FIELDS:
		value = figures.get(field)
		if field == "penalty_rule":
			doc.set(field, (value or "").strip() or None)
		elif field == "cap_at_tax":
			doc.set(field, cint(value))
		else:
			doc.set(field, flt(value))
	doc.save()
	return figures_of(template)


def use_library_figures(template: str) -> dict:
	"""Back to the library's figures: the firm's own are removed."""
	name = firm_figures([template]).get(template, {}).get("name")
	if name:
		frappe.delete_doc(DOCTYPE, name)
	return figures_of(template)
