import frappe
from frappe.utils import add_days, getdate

LICENSE_CHILD_DOCTYPES = ("Drug License Details", "FSSAI Details")


def logger():
	return frappe.logger("compliance_plus")


def already_sent_recently(customer, interval_days):
	threshold_date = add_days(getdate(), -interval_days)
	return frappe.db.exists(
		"Communication",
		{
			"reference_doctype": "Customer",
			"reference_name": customer,
			"communication_type": "Automated Message",
			"creation": [">", threshold_date],
		},
	)


def log_communication(customer, subject):
	frappe.get_doc(
		{
			"doctype": "Communication",
			"communication_type": "Automated Message",
			"subject": subject,
			"reference_doctype": "Customer",
			"reference_name": customer,
			"content": subject,
			"sent_or_received": "Sent",
		}
	).insert(ignore_permissions=True)


def send_license_expiry_reminders():
	missing = [dt for dt in LICENSE_CHILD_DOCTYPES if not frappe.db.exists("DocType", dt)]
	if missing:
		# Most sites do not keep licence details on Customer; that is not an error.
		logger().info(f"Customer licence reminders skipped: missing DocTypes {', '.join(missing)}")
		return

	settings = frappe.get_single("Compliance Plus Settings")
	expiry_threshold = settings.expiry_threshold or 15
	set_interval = settings.set_interval or 15
	sender = settings.sender
	template_name = settings.email_template

	if not sender or not template_name:
		logger().info("Customer licence reminders skipped: no sender or email template set")
		return

	try:
		template = frappe.get_doc("Email Template", template_name)
	except frappe.DoesNotExistError:
		frappe.log_error(
			title="Customer licence reminders: email template not found",
			message=f"Email Template {template_name} in Compliance Plus Settings does not exist.",
		)
		return

	today = getdate()
	target_expiry_date = add_days(today, expiry_threshold)

	customers = frappe.get_all(
		"Customer", filters={"disabled": 0}, fields=["name", "customer_name", "email_id"]
	)

	sent = 0
	for customer in customers:
		if not customer.email_id or already_sent_recently(customer.name, set_interval):
			continue

		dl_details = frappe.get_all(
			"Drug License Details",
			filters={"parent": customer.name, "expiry_date": ["between", [today, target_expiry_date]]},
			fields=["license_number", "expiry_date"],
		)

		fssai_details = frappe.get_all(
			"FSSAI Details",
			filters={"parent": customer.name, "expiry_date": ["between", [today, target_expiry_date]]},
			fields=["license_number", "expiry_date"],
		)

		if not dl_details and not fssai_details:
			continue

		context = {
			"doc": {
				"customer_name": customer.customer_name,
				"company": frappe.defaults.get_global_default("company"),
				"fsl_dl_details": dl_details,
				"fsl_fssai_details": fssai_details,
			}
		}

		try:
			message = frappe.render_template(template.response, context)
		except Exception:
			frappe.log_error(title=f"Customer licence reminder could not be rendered for {customer.name}")
			continue

		try:
			frappe.sendmail(
				recipients=[customer.email_id],
				sender=sender,
				subject=template.subject,
				message=message,
			)
			log_communication(customer.name, template.subject)
			sent += 1
		except Exception:
			frappe.log_error(title=f"Customer licence reminder could not be sent to {customer.name}")

	logger().info(f"Customer licence reminders queued: {sent}")
