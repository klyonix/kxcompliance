# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""A CA/CS firm's clients: which companies each owns, and who on the firm's team sees them.

A Compliance User on a client's team gets a User Permission on each of the client's
companies, so Frappe keeps them to those companies everywhere, and permissions.py lets
them see every record there. The app notes each access in Compliance Client Access and
only ever removes the User Permissions it made itself.
"""

import frappe
from frappe.utils import add_days, nowdate

from compliance_plus.compliance_plus.register import CLOSED_TASK_STATUSES
from compliance_plus.permissions import is_restricted

ACCESS = "Compliance Client Access"


def client_companies(client: str) -> list[str]:
	return frappe.get_all("Company Compliance Profile", filters={"client": client}, pluck="company")


def team_of(client) -> set[str]:
	"""Everyone who works on a client: the relationship manager and the team."""
	people = {row.user for row in client.team if row.user}
	if client.relationship_manager:
		people.add(client.relationship_manager)
	return people


def wanted_access(client) -> set[tuple[str, str]]:
	"""(user, company) pairs the client's team should have. Managers see every client already,
	and a User Permission would only narrow what they see, so they are left out."""
	if client.status == "Left":
		return set()
	people = {user for user in team_of(client) if is_restricted(user)}
	return {(user, company) for user in people for company in client_companies(client.name)}


def sync_client_access(client_name: str):
	"""Bring a client's access records and User Permissions in line with its team and companies."""
	client = (
		frappe.get_doc("Compliance Client", client_name)
		if frappe.db.exists("Compliance Client", client_name)
		else None
	)
	wanted = wanted_access(client) if client else set()
	existing = frappe.get_all(
		ACCESS, filters={"client": client_name}, fields=["name", "user", "company", "made_user_permission"]
	)
	have = {(row.user, row.company) for row in existing}
	for row in existing:
		if (row.user, row.company) not in wanted:
			remove_access(row)
	for user, company in wanted - have:
		add_access(client_name, user, company)


def add_access(client: str, user: str, company: str):
	made = False
	if not frappe.db.exists("User Permission", {"user": user, "allow": "Company", "for_value": company}):
		permission = frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": "Company",
				"for_value": company,
				"apply_to_all_doctypes": 1,
			}
		)
		# Kept by the app for the client's team, not by the person editing the client.
		permission.insert(ignore_permissions=True)
		made = True
	access = frappe.get_doc(
		{"doctype": ACCESS, "client": client, "user": user, "company": company, "made_user_permission": made}
	)
	access.insert(ignore_permissions=True)  # the app's own record of the access above


def remove_access(row):
	frappe.delete_doc(ACCESS, row.name, ignore_permissions=True)  # the app's own record
	if not row.made_user_permission:
		return
	# Another client of the same company may still give this person access to it.
	still_needed = frappe.db.exists(ACCESS, {"user": row.user, "company": row.company})
	if still_needed:
		frappe.db.set_value(ACCESS, still_needed, "made_user_permission", 1)
		return
	permission = frappe.db.get_value(
		"User Permission", {"user": row.user, "allow": "Company", "for_value": row.company}
	)
	if permission:
		frappe.delete_doc("User Permission", permission, ignore_permissions=True)


COUNT = {"COUNT": "*", "as": "count"}
TASK_FIELDS = [
	"name",
	"obligation_template",
	"period_label",
	"company",
	"status",
	"is_overdue",
	"effective_due_date",
	"filed_on",
]


def filing_counts(companies: list[str]) -> dict[str, dict[str, int]]:
	"""Per company: open filings overdue, due in the next seven days, and waiting for review.
	Read with get_list, so each person counts only what they may see."""
	counts = {company: {"overdue": 0, "due_this_week": 0, "in_review": 0} for company in companies}
	if not companies:
		return counts
	open_filings = {"company": ("in", companies), "status": ("not in", CLOSED_TASK_STATUSES)}
	for row in frappe.get_list(
		"Compliance Task",
		filters=open_filings,
		fields=["company", "status", "is_overdue", COUNT],
		group_by="company, status, is_overdue",
		order_by=None,
	):
		if row.is_overdue:
			counts[row.company]["overdue"] += row["count"]
		if row.status == "Ready for Review":
			counts[row.company]["in_review"] += row["count"]
	today = nowdate()
	for row in frappe.get_list(
		"Compliance Task",
		filters={**open_filings, "effective_due_date": ("between", [today, add_days(today, 7)])},
		fields=["company", COUNT],
		group_by="company",
		order_by=None,
	):
		counts[row.company]["due_this_week"] = row["count"]
	return counts


def add_up(counts: dict[str, dict[str, int]], companies: list[str]) -> dict[str, int]:
	return {
		key: sum(counts[company][key] for company in companies)
		for key in ("overdue", "due_this_week", "in_review")
	}


def clients_overview() -> list[dict]:
	"""Every client the person may see, with its companies and open filings, worst first."""
	clients = frappe.get_list(
		"Compliance Client",
		filters={"status": ("!=", "Left")},
		fields=["name", "client_kind", "status", "relationship_manager"],
		order_by="name asc",
		limit=500,
	)
	if not clients:
		return []
	# Which companies each client owns; the names only, for clients the person may already read.
	profiles = frappe.get_all(
		"Company Compliance Profile",
		filters={"client": ("in", [row.name for row in clients])},
		fields=["company", "client"],
	)
	companies_of: dict[str, list[str]] = {}
	for row in profiles:
		companies_of.setdefault(row.client, []).append(row.company)
	counts = filing_counts([row.company for row in profiles])
	for row in clients:
		row.companies = sorted(companies_of.get(row.name, []))
		row.update(add_up(counts, row.companies))
	return sorted(clients, key=lambda row: (-row.overdue, -row.due_this_week, row.name))


def client_detail(name: str) -> dict:
	client = frappe.get_doc("Compliance Client", name)
	client.check_permission("read")
	companies = frappe.get_all(
		"Company Compliance Profile",
		filters={"client": name},
		fields=["company", "company_type"],
		order_by="company asc",
	)
	names = [row.company for row in companies]
	counts = filing_counts(names)
	for row in companies:
		row.update(counts[row.company])
	filings = (
		frappe.get_list(
			"Compliance Task",
			filters={"company": ("in", names), "status": ("not in", CLOSED_TASK_STATUSES)},
			fields=TASK_FIELDS,
			order_by="effective_due_date asc",
			limit=100,
		)
		if names
		else []
	)
	return {
		"name": client.name,
		"client_kind": client.client_kind,
		"status": client.status,
		"relationship_manager": client.relationship_manager,
		"team": [row.user for row in client.team],
		"contact_email": client.contact_email,
		"contact_phone": client.contact_phone,
		"companies": companies,
		"filings": filings,
		**add_up(counts, names),
	}
