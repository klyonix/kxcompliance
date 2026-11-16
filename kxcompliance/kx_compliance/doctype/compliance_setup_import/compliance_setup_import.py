# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr

from kxcompliance import scoped
from kxcompliance.kx_compliance.register import get_settings
from kxcompliance.kx_compliance.setup_import import check_rows, read_sheet, set_up

COMMIT_EVERY = 20


class ComplianceSetupImport(Document):
	def validate(self):
		self.total_rows = len(self.rows)
		self.made = sum(1 for row in self.rows if row.outcome == "Made")
		self.skipped = sum(1 for row in self.rows if row.outcome == "Skipped")
		self.failed = sum(1 for row in self.rows if row.outcome in ("Error", "Failed"))

	@frappe.whitelist(methods=["POST"])
	def check_sheet(self):
		"""Read the uploaded sheet and check every row; nothing is made yet."""
		self.check_permission("write")
		if self.status not in ("Draft", "Checked"):
			frappe.throw(
				_("This import is {0}; start a new one to check another sheet.").format(_(self.status))
			)
		files = scoped.get_all(
			"File",
			filters={"attached_to_doctype": self.doctype, "attached_to_name": self.name},
			fields=["name", "file_name", "file_url"],
			order_by="creation desc",
			limit=1,
		)
		if not files:
			frappe.throw(_("Upload the filled-in template first."))
		sheet = frappe.get_doc("File", files[0].name)
		rows = read_sheet(sheet.get_content(), sheet.file_name)
		self.file = sheet.file_url
		self.set("rows", [])
		for row in check_rows(rows, get_settings().account_type or ""):
			values = row.pop("values", None)
			self.append("rows", {**row, "values": json.dumps(values) if values else None})
		self.status = "Checked"
		self.save()

	@frappe.whitelist(methods=["POST"])
	def start_import(self):
		self.check_permission("write")
		if self.status != "Checked":
			frappe.throw(_("Check the sheet before importing it."))
		if not any(row.outcome == "Ready" for row in self.rows):
			frappe.throw(_("No row is ready to import; fix the sheet and check it again."))
		self.status = "Queued"
		self.save()
		frappe.enqueue(
			"frappe.utils.background_jobs.run_doc_method",
			doctype=self.doctype,
			name=self.name,
			doc_method="run_import",
			queue="long",
			timeout=3600,
			enqueue_after_commit=True,
		)

	def run_import(self):
		"""The background job: set up each ready row in its own savepoint."""
		self.status = "Importing"
		self.save()
		# A job: show the import as running while it runs.
		frappe.db.commit()  # nosemgrep
		ready = [row for row in self.rows if row.outcome == "Ready"]
		for count, row in enumerate(ready, start=1):
			frappe.db.savepoint("setup_row")
			try:
				row.tasks = set_up(json.loads(row.values))
				row.outcome = "Made"
				row.message = _("Set up, with {0} filings.").format(row.tasks)
			except Exception as error:
				frappe.db.rollback(save_point="setup_row")
				frappe.log_error(title=_("Bulk setup failed for {0}").format(row.company))
				row.outcome = "Failed"
				row.message = cstr(error) or _("Could not be set up; see the Error Log.")
			if count % COMMIT_EVERY == 0:
				self.save()
				# A job: keep what is done if a later row brings the job down.
				frappe.db.commit()  # nosemgrep
		self.status = "Done with Errors" if any(row.outcome == "Failed" for row in self.rows) else "Done"
		self.save()
