import click
import frappe

from kxcompliance.kx_compliance.move_old_trackers import move_customer_licences


def execute():
	for doctype, counts in move_customer_licences().items():
		frappe.logger("kxcompliance").info(f"Moved {doctype} into Compliance Item: {counts}")
		if counts["failed"]:
			click.secho(
				f"{doctype}: {counts['failed']} row(s) could not be moved to Compliance Item; "
				"see the Error Log, fix them, and run move_customer_licences again.",
				fg="yellow",
			)
