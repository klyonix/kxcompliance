# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""The scheduled jobs, each handed to scoped.run_job so another app may run it its own way."""

from kxcompliance import scoped
from kxcompliance.kx_compliance import billing, document_requests, legal, privacy, reminders, statutory


def reminders_daily():
	scoped.run_job(reminders.run_daily)


def statutory_daily():
	scoped.run_job(statutory.run_daily)


def legal_daily():
	scoped.run_job(legal.run_daily)


def document_requests_daily():
	scoped.run_job(document_requests.run_daily)


def privacy_daily():
	scoped.run_job(privacy.run_daily)


def billing_overdue_reminders():
	scoped.run_job(billing.send_overdue_reminders)


def billing_monthly_drafts():
	scoped.run_job(billing.make_monthly_drafts)
