# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""Show a party's licences on the Customer and Supplier dashboards."""

from frappe import _


def with_licences(data, party_type: str):
	data.setdefault("non_standard_fieldnames", {})["Compliance Item"] = "holder"
	data.setdefault("dynamic_links", {})["holder"] = [party_type, "holder_type"]
	data.setdefault("transactions", []).append({"label": _("Compliance"), "items": ["Compliance Item"]})
	return data


def customer(data):
	return with_licences(data, "Customer")


def supplier(data):
	return with_licences(data, "Supplier")
