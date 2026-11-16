# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Bulk setup: a firm's clients and companies from one spreadsheet, one row per company.

A row names the client, the company and its kind, the people who handle it, and its
registrations. Every row is checked first and shown before anything is made. Importing then
sets each ready company up as onboarding does: the ERPNext company if it is new, the client if
it is new, the compliance profile with its registrations, its obligations and first filings.
A company already set up is skipped and never changed. Client logins are not in the sheet, so
an import never emails a client.
"""

import re

import frappe
from frappe import _
from frappe.utils import cstr
from frappe.utils.csvutils import read_csv_content
from frappe.utils.xlsxutils import make_xlsx, read_xlsx_file_from_attached_file

from kxcompliance import scoped
from kxcompliance.kx_compliance.onboarding import (
	STATE_REGISTRATIONS,
	clean_registrations,
	make_company,
	select_options,
	set_up_company,
)

MAX_ROWS = 500
# The sheet's columns, in order: (heading, key).
COLUMNS = (
	("Client", "client"),
	("Client Kind", "client_kind"),
	("Company", "company"),
	("Company Kind", "company_type"),
	("Responsible", "responsible"),
	("Reviewer", "reviewer"),
	("Relationship Manager", "relationship_manager"),
	("Team", "team"),
	("GSTIN", "gstin"),
	("GST Composition", "gst_composition"),
	("TAN", "tan"),
	("PF", "pf"),
	("ESI", "esi"),
	("PT", "pt"),
	("PT State", "pt_state"),
	("LWF", "lwf"),
	("LWF State", "lwf_state"),
	("IEC", "iec"),
	("FSSAI", "fssai"),
	("Stock Exchange", "stock_exchange"),
)
EXAMPLE = {
	"client": "Sunrise Group",
	"client_kind": "Business Group",
	"company": "Sunrise Foods Private Limited",
	"company_type": "Private Limited",
	"responsible": "staff@yourfirm.example.com",
	"reviewer": "partner@yourfirm.example.com",
	"relationship_manager": "partner@yourfirm.example.com",
	"team": "staff@yourfirm.example.com, article@yourfirm.example.com",
	"gstin": "29AAKCS1234F1Z5, 27AAKCS1234F1Z7",
	"gst_composition": "No",
	"tan": "BLRS12345A",
	"pf": "KNBNG1234567000",
	"esi": "53000123450001001",
	"pt": "PTKA123456",
	"pt_state": "Karnataka",
}
# Simple registrations: a column holding the number.
NUMBER_COLUMNS = {
	"tan": "TAN",
	"pf": "PF",
	"esi": "ESI",
	"iec": "IEC",
	"fssai": "FSSAI",
	"stock_exchange": "Stock Exchange",
}
STATE_COLUMNS = {"pt": ("PT", "pt_state"), "lwf": ("LWF", "lwf_state")}
GSTIN_PATTERN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
# The state a GSTIN belongs to, from its first two digits.
GST_STATE_CODES = {
	"01": "Jammu and Kashmir",
	"02": "Himachal Pradesh",
	"03": "Punjab",
	"04": "Chandigarh",
	"05": "Uttarakhand",
	"06": "Haryana",
	"07": "Delhi",
	"08": "Rajasthan",
	"09": "Uttar Pradesh",
	"10": "Bihar",
	"11": "Sikkim",
	"12": "Arunachal Pradesh",
	"13": "Nagaland",
	"14": "Manipur",
	"15": "Mizoram",
	"16": "Tripura",
	"17": "Meghalaya",
	"18": "Assam",
	"19": "West Bengal",
	"20": "Jharkhand",
	"21": "Odisha",
	"22": "Chhattisgarh",
	"23": "Madhya Pradesh",
	"24": "Gujarat",
	"25": "Dadra and Nagar Haveli and Daman and Diu",
	"26": "Dadra and Nagar Haveli and Daman and Diu",
	"27": "Maharashtra",
	"29": "Karnataka",
	"30": "Goa",
	"31": "Lakshadweep",
	"32": "Kerala",
	"33": "Tamil Nadu",
	"34": "Puducherry",
	"35": "Andaman and Nicobar Islands",
	"36": "Telangana",
	"37": "Andhra Pradesh",
	"38": "Ladakh",
}
YES = {"yes", "y", "true", "1"}


def template() -> bytes:
	"""The sheet to fill in: the headings and one example row."""
	data = [
		[heading for heading, _key in COLUMNS],
		[EXAMPLE.get(key, "") for _heading, key in COLUMNS],
	]
	return make_xlsx(data, "Companies").getvalue()


def read_sheet(content: bytes, file_name: str) -> list[dict]:
	"""The sheet's rows as {key: text}, by heading (any case, any order); empty rows left out."""
	if file_name.lower().endswith(".csv"):
		table = read_csv_content(content)
	elif file_name.lower().endswith(".xlsx"):
		table = read_xlsx_file_from_attached_file(fcontent=content)
	else:
		frappe.throw(_("Upload the template as an .xlsx or .csv file."))
	if not table:
		frappe.throw(_("The sheet is empty."))
	keys = {heading.lower(): key for heading, key in COLUMNS}
	headings = [keys.get(cstr(cell).strip().lower()) for cell in table[0]]
	if "company" not in headings:
		frappe.throw(_("The first row should be the template's headings, with a Company column."))
	rows = []
	for number, cells in enumerate(table[1:], start=2):
		values = {key: cstr(cell).strip() for key, cell in zip(headings, cells, strict=False) if key}
		if any(values.values()):
			rows.append({"row_number": number, **values})
	if len(rows) > MAX_ROWS:
		frappe.throw(_("The sheet has {0} rows; import at most {1} at a time.").format(len(rows), MAX_ROWS))
	return rows


def split(text: str) -> list[str]:
	return [part.strip() for part in re.split(r"[,;\n]", text or "") if part.strip()]


def registrations_of(row: dict) -> list[dict]:
	"""The row's registrations, as the compliance profile takes them; throws on the first problem."""
	found = []
	kind = "GST Composition" if (row.get("gst_composition") or "").lower() in YES else "GST"
	for gstin in split(row.get("gstin")):
		gstin = gstin.upper()
		if not GSTIN_PATTERN.match(gstin):
			frappe.throw(_("GSTIN {0} is not 15 characters in the GSTIN pattern.").format(gstin))
		state = GST_STATE_CODES.get(gstin[:2])
		if not state:
			frappe.throw(_("GSTIN {0} starts with {1}, which is not a state code.").format(gstin, gstin[:2]))
		found.append({"registration_type": kind, "registration_number": gstin, "state": state})
	for key, kind in NUMBER_COLUMNS.items():
		for number in split(row.get(key)):
			found.append({"registration_type": kind, "registration_number": number})
	for key, (kind, state_key) in STATE_COLUMNS.items():
		for number in split(row.get(key)):
			found.append(
				{"registration_type": kind, "registration_number": number, "state": row.get(state_key) or ""}
			)
	return clean_registrations(found)


def people_on_site(rows: list[dict]) -> set[str]:
	"""Every person the sheet names who is an active firm user here, in one query."""
	named = set()
	for row in rows:
		named.update(split(row.get("team")))
		named.update(
			row.get(key) for key in ("responsible", "reviewer", "relationship_manager") if row.get(key)
		)
	if not named:
		return set()
	return set(
		scoped.get_all(
			"User",
			filters={"name": ("in", list(named)), "enabled": 1, "user_type": "System User"},
			pluck="name",
		)
	)


def check_rows(rows: list[dict], account_type: str) -> list[dict]:
	"""Each row with its outcome (Ready, Error or Skipped), what will happen, and the clean values."""
	company_types = set(select_options("Company Compliance Profile", "company_type"))
	client_kinds = set(select_options("Compliance Client", "client_kind"))
	people = people_on_site(rows)
	companies = {row.get("company") for row in rows if row.get("company")}
	existing = set(scoped.get_all("Company", filters={"name": ("in", list(companies) or [""])}, pluck="name"))
	set_up = set(
		scoped.get_all(
			"Company Compliance Profile",
			filters={"company": ("in", list(companies) or [""])},
			pluck="company",
		)
	)
	clients = {row.get("client") for row in rows if row.get("client")}
	known_clients = set(
		scoped.get_all("Compliance Client", filters={"name": ("in", list(clients) or [""])}, pluck="name")
	)
	can_create = frappe.has_permission("Company", "create")
	may_create = bool(can_create) and bool(frappe.is_setup_complete())
	firm = account_type == "CA/CS Firm"
	seen = {}
	checked = []
	for row in rows:
		result = {
			"row_number": row["row_number"],
			"client": row.get("client", ""),
			"company": row.get("company", ""),
		}
		try:
			values = check_row(row, firm, company_types, client_kinds, people)
		except frappe.ValidationError as error:
			checked.append({**result, "outcome": "Error", "message": cstr(error)})
			continue
		company = values["company"]
		if company in seen:
			checked.append(
				{
					**result,
					"outcome": "Error",
					"message": _("{0} is also on row {1}.").format(company, seen[company]),
				}
			)
			continue
		seen[company] = row["row_number"]
		if company in set_up:
			checked.append(
				{
					**result,
					"outcome": "Skipped",
					"message": _("Already set up for compliance; left as it is."),
				}
			)
			continue
		if company not in existing and not may_create:
			checked.append(
				{
					**result,
					"outcome": "Error",
					"message": _("{0} is not an ERPNext company, and you cannot create companies.").format(
						company
					),
				}
			)
			continue
		values["new_company"] = company not in existing
		values["new_client"] = bool(values["client"]) and values["client"] not in known_clients
		checked.append({**result, "outcome": "Ready", "message": plan(values), "values": values})
	return checked


def check_row(row: dict, firm: bool, company_types, client_kinds, people) -> dict:
	company = row.get("company")
	if not company:
		frappe.throw(_("Give the company's name."))
	client = row.get("client") or ""
	if firm and not client:
		frappe.throw(_("Give the client that {0} belongs to.").format(company))
	if row.get("company_type") not in company_types:
		frappe.throw(_("Company Kind should be one of: {0}.").format(", ".join(sorted(company_types))))
	client_kind = row.get("client_kind") or "Business Group"
	if client_kind not in client_kinds:
		frappe.throw(_("Client Kind should be one of: {0}.").format(", ".join(sorted(client_kinds))))
	for key, label in (
		("responsible", _("Responsible")),
		("reviewer", _("Reviewer")),
		("relationship_manager", _("Relationship Manager")),
	):
		if row.get(key) and row[key] not in people:
			frappe.throw(_("{0} {1} is not an active user of this site.").format(label, row[key]))
	if not row.get("responsible"):
		frappe.throw(_("Give who is responsible for {0}'s filings (their login email).").format(company))
	team = split(row.get("team"))
	for user in team:
		if user not in people:
			frappe.throw(_("Team member {0} is not an active user of this site.").format(user))
	for key, (kind, state_key) in STATE_COLUMNS.items():
		if row.get(key) and kind in STATE_REGISTRATIONS and not row.get(state_key):
			frappe.throw(_("Give the {0} State for the {0} registration.").format(kind))
	return {
		"client": client,
		"client_kind": client_kind,
		"company": company,
		"company_type": row["company_type"],
		"responsible": row["responsible"],
		"reviewer": row.get("reviewer") or None,
		"relationship_manager": row.get("relationship_manager") or None,
		"team": team,
		"registrations": registrations_of(row),
	}


def plan(values: dict) -> str:
	"""What importing the row will do, in a line."""
	parts = []
	if values["client"]:
		parts.append(_("New client") if values["new_client"] else _("Existing client"))
	parts.append(_("new company") if values["new_company"] else _("existing ERPNext company"))
	parts.append(values["company_type"])
	kinds: dict[str, int] = {}
	for row in values["registrations"]:
		kinds[row["registration_type"]] = kinds.get(row["registration_type"], 0) + 1
	if kinds:
		parts.append(", ".join(f"{kind} ({count})" if count > 1 else kind for kind, count in kinds.items()))
	return " · ".join(parts)


def set_up(values: dict) -> int:
	"""Make what a ready row describes; returns the number of filings made."""
	client = values["client"] or None
	if client and not scoped.exists("Compliance Client", client):
		frappe.get_doc(
			{
				"doctype": "Compliance Client",
				"client_name": client,
				"client_kind": values["client_kind"],
				"relationship_manager": values["relationship_manager"] or frappe.session.user,
				"team": [{"user": user} for user in values["team"]],
			}
		).insert()
	company = values["company"]
	if not scoped.exists("Company", company):
		make_company(company)
	if scoped.exists("Company Compliance Profile", company):
		frappe.throw(_("{0} was set up for compliance after the sheet was checked.").format(company))
	_obligations, tasks = set_up_company(
		company,
		values["company_type"],
		values["responsible"],
		values["reviewer"],
		values["registrations"],
		client,
	)
	return tasks
