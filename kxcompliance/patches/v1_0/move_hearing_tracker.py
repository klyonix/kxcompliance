import click
import frappe

from kxcompliance.kx_compliance.move_old_trackers import move_hearings


def execute():
	counts = move_hearings()
	frappe.logger("kxcompliance").info(f"Moved Hearing Tracker into Legal Case: {counts}")
	if counts["failed"]:
		click.secho(
			f"Hearing Tracker: {counts['failed']} row(s) could not be moved to Legal Case; "
			"see the Error Log, fix them, and run move_hearings again.",
			fg="yellow",
		)
