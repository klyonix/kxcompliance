import click
import frappe

from kxcompliance.kx_compliance.move_old_trackers import move_trademarks


def execute():
	counts = move_trademarks()
	frappe.logger("kxcompliance").info(f"Moved Trademark Tracker into Trademark: {counts}")
	if counts["failed"]:
		click.secho(
			f"Trademark Tracker: {counts['failed']} row(s) could not be moved to Trademark; "
			"see the Error Log, fix them, and run move_trademarks again.",
			fg="yellow",
		)
