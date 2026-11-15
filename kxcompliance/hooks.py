app_name = "kxcompliance"
app_title = "KlyONIX Compliance"
app_publisher = "KlyONIX Tech Consulting Pvt Ltd"
app_description = "Simple Compliance Management app"
app_email = "hello@klyonix.com"
app_license = "agpl-3.0"

# Apps
# ------------------

required_apps = ["erpnext"]

# The app on the apps page; the site's default app (install.set_branding), so sign-in lands here.
add_to_apps_screen = [
	{
		"name": "kxcompliance",
		"logo": "/assets/kxcompliance/frontend/icon-192.png",
		"title": "KlyONIX Compliance",
		"route": "/compliance",
		"has_permission": "kxcompliance.api.can_open_app",
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/kxcompliance/css/kxcompliance.css"
# app_include_js = "/assets/kxcompliance/js/kxcompliance.js"

# include js, css files in header of web template
# web_include_css = "/assets/kxcompliance/css/kxcompliance.css"
# web_include_js = "/assets/kxcompliance/js/kxcompliance.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "kxcompliance/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "kxcompliance/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# A client login has no Desk; signing in takes them straight to the app.
role_home_page = {"Compliance Client": "compliance"}

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# The firm's bills and receipts print with these (print_format/klyonix_bill, klyonix_receipt).
jinja = {
	"methods": [
		"kxcompliance.kx_compliance.billing.bill_print",
		"kxcompliance.kx_compliance.billing.receipt_print",
	],
}
# jinja = {
# 	"methods": "kxcompliance.utils.jinja_methods",
# 	"filters": "kxcompliance.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "kxcompliance.install.before_install"
# after_install = "kxcompliance.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "kxcompliance.uninstall.before_uninstall"
# after_uninstall = "kxcompliance.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "kxcompliance.utils.before_app_install"
# after_app_install = "kxcompliance.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "kxcompliance.utils.before_app_uninstall"
# after_app_uninstall = "kxcompliance.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "kxcompliance.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
	# 	"all": [
	# 		"kxcompliance.tasks.all"
	# 	],
	"daily": [
		"kxcompliance.kx_compliance.reminders.run_daily",
		"kxcompliance.kx_compliance.statutory.run_daily",
		"kxcompliance.kx_compliance.legal.run_daily",
		"kxcompliance.kx_compliance.document_requests.run_daily",
		"kxcompliance.kx_compliance.privacy.run_daily",
		"kxcompliance.kx_compliance.billing.send_overdue_reminders",
	],
	# 	"hourly": [
	# 		"kxcompliance.tasks.hourly"
	# 	],
	# 	"weekly": [
	# 		"kxcompliance.tasks.weekly"
	# 	],
	"monthly": [
		"kxcompliance.kx_compliance.billing.make_monthly_drafts",
	],
}

# Testing
# -------

# before_tests = "kxcompliance.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "kxcompliance.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "kxcompliance.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["kxcompliance.utils.before_request"]
# after_request = ["kxcompliance.utils.after_request"]

# Job Events
# ----------
# before_job = ["kxcompliance.utils.before_job"]
# after_job = ["kxcompliance.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"kxcompliance.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }


after_install = "kxcompliance.install.after_install"
after_migrate = "kxcompliance.install.after_migrate"

permission_query_conditions = {
	"Compliance Client": "kxcompliance.permissions.client_query_conditions",
	"Compliance Item": "kxcompliance.permissions.item_query_conditions",
	"Compliance List View": "kxcompliance.permissions.list_view_query_conditions",
	"Compliance Renewal": "kxcompliance.permissions.renewal_query_conditions",
	"Compliance Task": "kxcompliance.permissions.task_query_conditions",
	"Document Request": "kxcompliance.permissions.document_request_query_conditions",
	"Legal Case": "kxcompliance.permissions.legal_case_query_conditions",
	"Legal Date": "kxcompliance.permissions.legal_date_query_conditions",
	"Trademark": "kxcompliance.permissions.trademark_query_conditions",
}

has_permission = {
	"Compliance Client": "kxcompliance.permissions.has_client_permission",
	"Compliance Item": "kxcompliance.permissions.has_item_permission",
	"Compliance List View": "kxcompliance.permissions.has_list_view_permission",
	"Compliance Renewal": "kxcompliance.permissions.has_renewal_permission",
	"Compliance Task": "kxcompliance.permissions.has_task_permission",
	"Document Request": "kxcompliance.permissions.has_document_request_permission",
	"Legal Case": "kxcompliance.permissions.has_legal_case_permission",
	"Legal Date": "kxcompliance.permissions.has_legal_date_permission",
	"Trademark": "kxcompliance.permissions.has_trademark_permission",
}

calendars = ["Compliance Item", "Compliance Task", "Legal Date"]

# Whoever holds a firm's work at another client's company still sees it (clients.py),
# and stops seeing it once they hold no open work there.
_HOLDERS_SEE = {
	"on_update": [
		"kxcompliance.kx_compliance.clients.let_holders_see",
		"kxcompliance.kx_compliance.clients.let_go_of_holders",
	],
	"after_delete": "kxcompliance.kx_compliance.clients.let_go_of_holders",
}

doc_events = {
	"Compliance Task": _HOLDERS_SEE,
	"Compliance Item": _HOLDERS_SEE,
	"Legal Case": _HOLDERS_SEE,
	"Trademark": _HOLDERS_SEE,
	"Legal Date": _HOLDERS_SEE,
	"Notification Log": {
		"before_insert": "kxcompliance.kx_compliance.app_links.point_notification_to_app",
	},
	"File": {
		"after_insert": "kxcompliance.kx_compliance.document_requests.take_emailed_file",
	},
	"Quotation": {
		"validate": "kxcompliance.kx_compliance.party_licences.check_document",
		"on_submit": "kxcompliance.kx_compliance.party_licences.check_document",
	},
	"Sales Order": {
		"validate": "kxcompliance.kx_compliance.party_licences.check_document",
		"on_submit": "kxcompliance.kx_compliance.party_licences.check_document",
	},
	"Delivery Note": {
		"validate": "kxcompliance.kx_compliance.party_licences.check_document",
		"on_submit": "kxcompliance.kx_compliance.party_licences.check_document",
	},
	"Sales Invoice": {
		"validate": "kxcompliance.kx_compliance.party_licences.check_document",
		"on_submit": [
			"kxcompliance.kx_compliance.party_licences.check_document",
			"kxcompliance.kx_compliance.billing.mark_filings_billed",
		],
		"on_cancel": "kxcompliance.kx_compliance.billing.unmark_filings_billed",
	},
	"Purchase Order": {
		"validate": "kxcompliance.kx_compliance.party_licences.check_document",
		"on_submit": "kxcompliance.kx_compliance.party_licences.check_document",
	},
	"Purchase Receipt": {
		"validate": "kxcompliance.kx_compliance.party_licences.check_document",
		"on_submit": "kxcompliance.kx_compliance.party_licences.check_document",
	},
	"Purchase Invoice": {
		"validate": "kxcompliance.kx_compliance.party_licences.check_document",
		"on_submit": "kxcompliance.kx_compliance.party_licences.check_document",
	},
}

override_doctype_dashboards = {
	"Customer": "kxcompliance.kx_compliance.party_dashboards.customer",
	"Supplier": "kxcompliance.kx_compliance.party_dashboards.supplier",
}

fixtures = [
	{
		"dt": "Custom Field",
		"filters": [
			[
				"name",
				"in",
				[
					"Sales Invoice-customer_licence_numbers",
					"Delivery Note-customer_licence_numbers",
					"Sales Invoice-compliance_client",
					"Sales Invoice-kx_billing_key",
					"Sales Invoice Item-compliance_task",
					"Sales Invoice Item-sac_code",
					"Sales Invoice-bill_title",
					"Sales Invoice-billed_company",
					"Payment Entry-paid_by_company",
				],
			]
		],
	}
]

# Every page of the app at /compliance is served by www/compliance.py, so a reload or a
# link into /compliance/account opens the app rather than a 404.
website_route_rules = [
	{"from_route": "/compliance/<path:app_path>", "to_route": "compliance"},
]
