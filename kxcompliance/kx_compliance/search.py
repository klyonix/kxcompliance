# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""The app's search: every word typed must appear in one of a record's searched fields, in any
order, so "gst pune 3b" finds the Pune company's GSTR-3B. Each kind of record is read with the
person's own permissions, and its closest matches come first: a name that is the words, then one
that starts with them, then the most recently changed.
"""

import frappe
from frappe.query_builder import Case, Criterion, Order
from frappe.query_builder.functions import Lower

from kxcompliance import compat, scoped
from kxcompliance.kx_compliance.register import client_titles

MIN_LENGTH = 2
# How many of each kind are looked at and returned; the screens show "30+" past that.
CANDIDATES = 30
MAX_WORDS = 6

# kind: (doctype, fields searched, fields returned, the field a match is ranked on)
KINDS = {
	"items": (
		"Compliance Item",
		["title", "reference_number", "item_type", "company"],
		["name", "title", "item_type", "status", "valid_until", "reference_number"],
		"title",
	),
	"filings": (
		"Compliance Task",
		["obligation_template", "acknowledgement_number", "period_label", "company"],
		[
			"name",
			"obligation_template",
			"period_label",
			"company",
			"status",
			"is_overdue",
			"effective_due_date",
			"filed_on",
		],
		"obligation_template",
	),
	"cases": (
		"Legal Case",
		["title", "case_number", "notice_reference", "cnr_number", "opposing_party", "company"],
		["name", "title", "case_type", "forum", "forum_name", "case_number", "status", "next_date"],
		"title",
	),
	"trademarks": (
		"Trademark",
		["mark", "application_number", "registration_number", "applicant"],
		["name", "mark", "application_number", "status", "next_date"],
		"mark",
	),
	"clients": (
		"Compliance Client",
		["name", "client_name", "contact_email"],
		["name", "client_name", "client_kind", "status"],
		"client_name",
	),
	"companies": (
		"Company Compliance Profile",
		["company", "client", "company_type"],
		["name", "company", "company_type", "client"],
		"company",
	),
	"signatories": (
		"Signatory",
		["full_name", "din", "company", "designation"],
		["name", "full_name", "designation", "company", "din", "is_active"],
		"full_name",
	),
	"requests": (
		"Document Request",
		["title", "name", "company", "filing_label"],
		["name", "title", "status", "company", "due_date", "filing_label", "is_overdue"],
		"title",
	),
	"rules": (
		"Licence Requirement",
		["item_type", "party_type"],
		["name", "item_type", "party_type", "action", "is_active"],
		"item_type",
	),
	"obligations": (
		"Compliance Obligation Template",
		["name", "form", "law"],
		[
			"name",
			"law",
			"form",
			"frequency",
			"months_after_period",
			"due_day",
			"due_after_event",
			"days_after_event",
			"event_type",
			"is_active",
			"is_standard",
		],
		"name",
	),
}


def words_of(text: str) -> list[str]:
	"""The words to look for: lower case, each at least once, and no more than a few."""
	seen = []
	for word in (text or "").lower().split():
		if word not in seen:
			seen.append(word)
	return seen[:MAX_WORDS]


def escape_like(text: str) -> str:
	"""Text for a LIKE pattern, with % and _ taken literally."""
	return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def like(word: str) -> str:
	"""A LIKE pattern that finds the word anywhere, as typed."""
	return f"%{escape_like(word)}%"


def rank(value: str, words: list[str]) -> int:
	"""0 when the ranked field is the words (in any order), 1 when it starts with them as typed,
	2 when all are in it, 3 otherwise (the words matched other fields)."""
	value = (value or "").lower()
	phrase = " ".join(words)
	if value == phrase or sorted(value.split()) == sorted(words):
		return 0
	if value.startswith(phrase):
		return 1
	if all(word in value for word in words):
		return 2
	return 3


def matching(kind: str, words: list[str], fields: list):
	"""The query for records of one kind with every word in some searched field, as far as the
	person may read them; None when they may not read that kind at all."""
	doctype, searched, _shown, _ranked = KINDS[kind]
	if not frappe.has_permission(doctype, "read"):
		return None
	table = frappe.qb.DocType(doctype)
	query = scoped.get_query(doctype, fields=fields, ignore_permissions=False)
	for word in words:
		pattern = like(word)
		query = query.where(Criterion.any([Lower(table[field]).like(pattern) for field in searched]))
	return query


def search_kind(kind: str, words: list[str], start: int = 0, limit: int = CANDIDATES) -> list[dict]:
	"""One page of the records of a kind with every word in some searched field, closest first."""
	doctype, _searched, shown, ranked = KINDS[kind]
	query = matching(kind, words, shown)
	if query is None:
		return []
	table = frappe.qb.DocType(doctype)
	# The closest come first in the database too, so an exact name is among those returned
	# however many newer records also match, and each page carries on from the last.
	phrase = " ".join(words)
	ranked_field = Lower(table[ranked])
	closeness = (
		Case()
		.when(ranked_field == phrase, 0)
		.when(ranked_field.like(f"{escape_like(phrase)}%"), 1)
		.when(Criterion.all([ranked_field.like(like(word)) for word in words]), 2)
		.else_(3)
	)
	rows = (
		query.orderby(closeness)
		.orderby(table.modified, order=Order.desc)
		.orderby(table.name)
		.offset(start)
		.limit(limit)
		.run(as_dict=True)
	)
	# Python's sort keeps the newest-first order among records that rank the same.
	return sorted(rows, key=lambda row: rank(row.get(ranked), words))


def count_kind(kind: str, words: list[str]) -> int:
	"""How many records of a kind the words find, as far as the person may read them."""
	query = matching(kind, words, [compat.agg("COUNT", "*", "count")])
	return query.run(as_dict=True)[0]["count"] if query is not None else 0


def search(
	text: str, kinds: list[str] | None = None, start: int = 0, limit: int = CANDIDATES
) -> dict[str, list]:
	"""Each kind's matches for `text`, a page of each; every kind is empty when it is too short."""
	words = words_of(text)
	chosen = [kind for kind in (kinds or KINDS) if kind in KINDS]
	if len(" ".join(words)) < MIN_LENGTH:
		return {kind: [] for kind in chosen}
	found = {kind: search_kind(kind, words, start, limit) for kind in chosen}
	if found.get("companies"):
		titles = client_titles(row.client for row in found["companies"])
		for row in found["companies"]:
			row.client_name = titles.get(row.client, "")
	return found


def counts(text: str, kinds: list[str] | None = None) -> dict[str, int]:
	"""How many each kind finds for `text`; nothing when it is too short to search."""
	words = words_of(text)
	chosen = [kind for kind in (kinds or KINDS) if kind in KINDS]
	if len(" ".join(words)) < MIN_LENGTH:
		return {kind: 0 for kind in chosen}
	return {kind: count_kind(kind, words) for kind in chosen}
