# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Prices before rate cards (Nov 2026) move onto them:
- the firm's price per return becomes the default "Standard" card;
- a client's own price per return becomes one of its own rates;
- its fixed fee becomes a recurring "Fixed fee" rate, billed from the date it was billed from.

The old fields are gone from the forms, so they are read from the tables they stay in. Safe to run
again: a default card is made only if there is none, and a client only if it has no own rates."""

import frappe

FREQUENCY_UNITS = {"Monthly": "Per month", "Quarterly": "Per quarter", "Yearly": "Per year"}


def execute():
	fee = frappe.qb.DocType("Return Fee")
	firm_prices = (
		frappe.qb.from_(fee)
		.select(fee.obligation_template, fee.amount)
		.where(fee.parenttype == "KX Compliance Settings")
		.orderby(fee.idx)
	).run(as_dict=True)
	if firm_prices and not frappe.db.exists("Rate Card", {"is_default": 1}):
		frappe.get_doc(
			{
				"doctype": "Rate Card",
				"title": "Standard" if not frappe.db.exists("Rate Card", "Standard") else "Standard (moved)",
				"is_default": 1,
				"description": "The firm's prices per return before rate cards.",
				"lines": [return_rate(row) for row in firm_prices],
			}
		).insert()

	own_prices: dict[str, list] = {}
	for row in (
		frappe.qb.from_(fee)
		.select(fee.parent, fee.obligation_template, fee.amount)
		.where(fee.parenttype == "Compliance Client")
		.orderby(fee.idx)
	).run(as_dict=True):
		own_prices.setdefault(row.parent, []).append(row)
	fixed = fixed_fees()
	for client in sorted(set(own_prices) | set(fixed)):
		doc = frappe.get_doc("Compliance Client", client)
		if doc.own_rates:
			continue
		for row in own_prices.get(client, []):
			doc.append("own_rates", return_rate(row))
		plan = fixed.get(client)
		if plan:
			doc.append(
				"own_rates",
				{
					"kind": "Service",
					"service": "Fixed fee",
					"unit": FREQUENCY_UNITS[plan.fee_frequency],
					"amount": plan.fixed_fee,
				},
			)
			doc.billing_from = doc.billing_from or plan.fee_from
		doc.save()


def return_rate(row) -> dict:
	return {
		"kind": "Return",
		"obligation_template": row.obligation_template,
		"unit": "Per filing",
		"amount": row.amount,
	}


def fixed_fees() -> dict:
	"""Clients' fixed fees, from the columns the old fields left (none on a site that never had them)."""
	if not frappe.db.has_column("Compliance Client", "fixed_fee"):
		return {}
	client = frappe.qb.DocType("Compliance Client")
	rows = (
		frappe.qb.from_(client)
		.select(client.name, client.fixed_fee, client.fee_frequency, client.fee_from)
		.where((client.fixed_fee > 0) & client.fee_frequency.isin(list(FREQUENCY_UNITS)))
	).run(as_dict=True)
	return {row.name: row for row in rows}
