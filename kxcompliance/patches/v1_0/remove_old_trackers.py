"""Remove the old trackers, which earlier releases moved into the register.

Their rows became Compliance Items, Legal Cases and Trademarks, each recording the row it came
from. A tracker row with no such record was never moved, so this stops rather than lose it.
"""

import frappe
from frappe import _

# Each old tracker and the doctype its rows were moved into.
OLD_TRACKERS = {
	"Compliance Tracker": "Compliance Item",
	"Licence Tracker": "Compliance Item",
	"Insurance Tracker": "Compliance Item",
	"Subscription Tracker": "Compliance Item",
	"Hearing Tracker": "Legal Case",
	"Trademark Tracker": "Trademark",
}
# Used only by Compliance Tracker.
OLD_MASTERS = ("Compliance Category",)
SHOWN_ROWS = 10


def execute():
	unmoved = rows_not_moved()
	if unmoved:
		frappe.throw(
			_(
				"These old tracker rows were never moved into the register: {0}. "
				"Go back to the previous release of KlyONIX Compliance, fix or delete them "
				"(see the Error Log for why each move failed), run migrate there, then update again."
			).format("; ".join(unmoved)),
			title=_("Old tracker rows not moved"),
		)

	for doctype in (*OLD_TRACKERS, *OLD_MASTERS):
		remove(doctype)


def rows_not_moved() -> list[str]:
	unmoved = []
	for doctype, target in OLD_TRACKERS.items():
		if not frappe.db.table_exists(doctype):
			continue
		old = frappe.qb.DocType(doctype)
		names = set((frappe.qb.from_(old).select(old.name)).run(pluck=True))
		if not names:
			continue
		new = frappe.qb.DocType(target)
		moved = set(
			(frappe.qb.from_(new).select(new.source_name).where(new.source_doctype == doctype)).run(
				pluck=True
			)
		)
		missing = sorted(names - moved)
		if missing:
			shown = ", ".join(missing[:SHOWN_ROWS])
			more = len(missing) - SHOWN_ROWS
			if more > 0:
				shown += " " + _("and {0} more").format(more)
			unmoved.append(f"{doctype}: {shown}")
	return unmoved


def remove(doctype: str):
	# Deleting a DocType keeps its table, so the table is dropped too. The query builder builds
	# DROP TABLE but cannot run it, hence sql_ddl. DDL commits on its own, which is safe here:
	# the record goes first and both steps can run again.
	frappe.delete_doc("DocType", doctype, force=True, ignore_missing=True)
	frappe.db.sql_ddl(frappe.qb.drop_table(f"tab{doctype}").if_exists().get_sql())
