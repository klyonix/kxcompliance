# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Whitelisted methods for the Compliance Plus app at /compliance."""

import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, now_datetime, nowdate

from compliance_plus.compliance_plus.register import CLOSED_TASK_STATUSES

APP_ROLES = frozenset({"System Manager", "Compliance Manager", "Compliance User", "Compliance Auditor"})
WORK_HORIZON_DAYS = 30
WORK_LIMIT = 200

# The only fields the app may change on each record; everything else stays in the Desk.
EDITABLE_FIELDS = {
	"Compliance Item": ("certificate", "reference_number", "notes"),
	"Compliance Task": (
		"status",
		"filed_on",
		"acknowledgement_number",
		"proof",
		"amount_paid",
		"interest",
		"late_fee",
		"remarks",
	),
	"Legal Date": ("status", "attended_by", "proceedings", "order", "next_date"),
}


def has_app_access(user: str | None = None) -> bool:
	return bool(APP_ROLES & set(frappe.get_roles(user)))


def check_app_access():
	if frappe.session.user == "Guest" or not has_app_access():
		frappe.throw(_("You do not have access to the compliance app."), frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def my_work() -> dict:
	"""What the signed-in person holds or reviews and should look at now, soonest first."""
	check_app_access()
	user = frappe.session.user
	mine = {"responsible": user, "reviewer": user}
	horizon = add_days(nowdate(), WORK_HORIZON_DAYS)
	return {
		"items": frappe.get_list(
			"Compliance Item",
			filters={
				"status": ("in", ["Draft", "Due for Renewal", "Expired", "Lapsed", "Renewal in Progress"])
			},
			or_filters=mine,
			fields=[
				"name",
				"title",
				"item_type",
				"status",
				"valid_until",
				"company",
				"responsible",
				"reviewer",
			],
			order_by="valid_until asc",
			limit=WORK_LIMIT,
		),
		"tasks": frappe.get_list(
			"Compliance Task",
			filters={"status": ("not in", CLOSED_TASK_STATUSES), "effective_due_date": ("<=", horizon)},
			or_filters=mine,
			fields=[
				"name",
				"obligation_template",
				"period_label",
				"company",
				"status",
				"is_overdue",
				"effective_due_date",
				"responsible",
				"reviewer",
			],
			order_by="effective_due_date asc",
			limit=WORK_LIMIT,
		),
		"legal_dates": frappe.get_list(
			"Legal Date",
			filters={"status": "Scheduled", "date": ("<=", horizon)},
			or_filters=mine,
			fields=[
				"name",
				"kind",
				"date",
				"reference_doctype",
				"reference_name",
				"reference_title",
				"is_overdue",
			],
			order_by="date asc",
			limit=WORK_LIMIT,
		),
		"as_of": str(now_datetime()),
	}


@frappe.whitelist(methods=["POST"])
def save_changes(doctype: str, name: str, values: dict, base_modified: str | None = None) -> dict:
	"""Save a few fields on a record, as the app does when online and when sending changes made offline.

	`base_modified` is the record's modified time when the change was made; if the record
	has changed since, the save is refused so nobody else's work is overwritten.
	"""
	check_app_access()
	allowed = EDITABLE_FIELDS.get(doctype)
	if not allowed:
		frappe.throw(_("The app cannot change {0}.").format(_(doctype)), frappe.PermissionError)
	not_allowed = sorted(set(values) - set(allowed))
	if not_allowed:
		frappe.throw(
			_("The app cannot change {0} on {1}.").format(", ".join(not_allowed), _(doctype)),
			frappe.PermissionError,
		)
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")
	if base_modified and get_datetime(doc.modified) != get_datetime(base_modified):
		frappe.throw(
			_("{0} {1} was changed by someone else after this change was made.").format(_(doctype), name),
			frappe.TimestampMismatchError,
		)
	doc.update(values)
	doc.save()
	return {"name": doc.name, "modified": str(doc.modified)}


def boot() -> dict:
	settings = frappe.get_cached_doc("Compliance Plus Settings")
	return {
		"user": frappe.session.user,
		"user_fullname": frappe.utils.get_fullname(frappe.session.user),
		"roles": sorted(APP_ROLES & set(frappe.get_roles())),
		"app_name": settings.app_name or "Compliance Plus",
		"app_logo": settings.app_logo or "",
		"csrf_token": frappe.sessions.get_csrf_token(),
		"site_name": frappe.local.site,
	}
