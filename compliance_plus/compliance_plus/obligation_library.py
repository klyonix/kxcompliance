# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""The standard obligation library shipped with the app.

The app owns these templates: every migrate brings their rules back to what is written
here, while a client's choice to switch one off is kept. A rule that changes by
government notification between releases is handled with a Compliance Due Date
Extension on the site, and here in the next release.

`checked_on` stays empty until a chartered accountant has confirmed the rule.
"""

import frappe

COMPANIES = ["Private Limited", "Public Limited", "One Person Company"]
QRMP_22_STATES = [
	"Andaman and Nicobar Islands", "Andhra Pradesh", "Chhattisgarh",
	"Dadra and Nagar Haveli and Daman and Diu", "Goa", "Gujarat", "Karnataka", "Kerala",
	"Lakshadweep", "Madhya Pradesh", "Maharashtra", "Puducherry", "Tamil Nadu", "Telangana",
]  # fmt: skip
QRMP_24_STATES = [
	"Arunachal Pradesh", "Assam", "Bihar", "Chandigarh", "Delhi", "Haryana", "Himachal Pradesh",
	"Jammu and Kashmir", "Jharkhand", "Ladakh", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
	"Odisha", "Punjab", "Rajasthan", "Sikkim", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
]  # fmt: skip
FILING_REMINDERS = (7, 2, 0)
YEARLY_REMINDERS = (30, 7, 1)


def obligation(name, law, form, frequency, months_after=None, day=None, **extra):
	values = {
		"template_name": name,
		"law": law,
		"form": form,
		"frequency": frequency,
		"period_basis": extra.pop("basis", "Financial Year"),
		"months_after_period": months_after,
		"due_day": day,
		"due_after_event": 0,
		"days_after_event": None,
		"overrides": [
			{"period_end_month": month, "months_after_period": after, "due_day": due_day}
			for month, after, due_day in extra.pop("overrides", ())
		],
		"company_types": [{"company_type": kind} for kind in extra.pop("companies", ())],
		"registration_type": extra.pop("registration", None),
		"states": "\n".join(extra.pop("states", ())),
		"add_by_default": extra.pop("default", 1),
		"requires_payment": extra.pop("payment", 0),
		"requires_proof": 1,
		"requires_review": 1,
		"reminders": [
			{"days_before": days}
			for days in extra.pop(
				"reminders", YEARLY_REMINDERS if frequency == "Yearly" else FILING_REMINDERS
			)
		],
		"authority": extra.pop("authority", None),
		"source": extra.pop("source", None),
		"checked_on": None,
	}
	if extra:
		raise ValueError(f"Unknown options for {name}: {sorted(extra)}")
	return values


def after_agm(name, form, days, source):
	values = obligation(
		name,
		"Companies Act",
		form,
		"Yearly",
		companies=COMPANIES,
		authority="Registrar of Companies",
		source=source,
	)
	values.update(
		{"due_after_event": 1, "days_after_event": days, "months_after_period": None, "due_day": None}
	)
	return values


def state_tax(law, state, frequency, months_after, day, registration, basis="Financial Year"):
	return obligation(
		f"{law} - {state}",
		law,
		None,
		frequency,
		months_after,
		day,
		basis=basis,
		registration=registration,
		states=[state],
		payment=1,
		source=f"{state} {law} rules; confirm the current due date before release.",
	)


GST = dict(registration="GST", authority="GST Network")
TAN = dict(registration="TAN", authority="Income Tax Department")

LIBRARY = [
	obligation("GSTR-1 (Monthly)", "GST", "GSTR-1", "Monthly", 1, 11, source="CGST Act s.37", **GST),
	obligation(
		"GSTR-1 (QRMP)",
		"GST",
		"GSTR-1",
		"Quarterly",
		1,
		13,
		default=0,
		source="CGST Act s.37, QRMP scheme",
		**GST,
	),
	obligation(
		"GSTR-3B (Monthly)",
		"GST",
		"GSTR-3B",
		"Monthly",
		1,
		20,
		payment=1,
		source="CGST Act s.39, rule 61",
		**GST,
	),
	obligation(
		"GSTR-3B (QRMP, 22nd)",
		"GST",
		"GSTR-3B",
		"Quarterly",
		1,
		22,
		payment=1,
		default=0,
		states=QRMP_22_STATES,
		source="CGST rule 61, QRMP scheme",
		**GST,
	),
	obligation(
		"GSTR-3B (QRMP, 24th)",
		"GST",
		"GSTR-3B",
		"Quarterly",
		1,
		24,
		payment=1,
		default=0,
		states=QRMP_24_STATES,
		source="CGST rule 61, QRMP scheme",
		**GST,
	),
	obligation("GSTR-9 (Annual Return)", "GST", "GSTR-9", "Yearly", 9, 31, source="CGST Act s.44", **GST),
	obligation(
		"GSTR-9C (Reconciliation)",
		"GST",
		"GSTR-9C",
		"Yearly",
		9,
		31,
		default=0,
		source="CGST Act s.44, rule 80(3)",
		**GST,
	),
	obligation(
		"TDS/TCS Payment",
		"TDS/TCS",
		"Challan ITNS 281",
		"Monthly",
		1,
		7,
		overrides=[(3, 1, 30)],
		payment=1,
		source="Income-tax Rules, rule 30",
		**TAN,
	),
	obligation(
		"TDS Return 24Q (Salary)",
		"TDS/TCS",
		"24Q",
		"Quarterly",
		1,
		31,
		overrides=[(3, 2, 31)],
		source="Income-tax Rules, rule 31A",
		**TAN,
	),
	obligation(
		"TDS Return 26Q (Non-salary)",
		"TDS/TCS",
		"26Q",
		"Quarterly",
		1,
		31,
		overrides=[(3, 2, 31)],
		source="Income-tax Rules, rule 31A",
		**TAN,
	),
	obligation(
		"TCS Return 27EQ",
		"TDS/TCS",
		"27EQ",
		"Quarterly",
		1,
		15,
		overrides=[(3, 2, 15)],
		default=0,
		source="Income-tax Rules, rule 31AA",
		**TAN,
	),
	obligation(
		"Form 16A",
		"TDS/TCS",
		"16A",
		"Quarterly",
		2,
		15,
		overrides=[(3, 3, 15)],
		source="Income-tax Rules, rule 31(3)",
		**TAN,
	),
	obligation("Form 16", "TDS/TCS", "16", "Yearly", 3, 15, source="Income-tax Rules, rule 31(3)", **TAN),
	obligation(
		"Advance Tax",
		"Income Tax",
		"Challan ITNS 280",
		"Quarterly",
		0,
		15,
		payment=1,
		authority="Income Tax Department",
		source="Income-tax Act s.211",
	),
	obligation(
		"Tax Audit Report",
		"Income Tax",
		"3CA/3CB-3CD",
		"Yearly",
		6,
		30,
		companies=COMPANIES,
		authority="Income Tax Department",
		source="Income-tax Act s.44AB",
	),
	obligation(
		"Income Tax Return (Audit Cases)",
		"Income Tax",
		"ITR-6",
		"Yearly",
		7,
		31,
		companies=COMPANIES,
		payment=1,
		authority="Income Tax Department",
		source="Income-tax Act s.139(1)",
	),
	obligation(
		"PF ECR and Payment",
		"PF",
		"ECR",
		"Monthly",
		1,
		15,
		registration="PF",
		payment=1,
		authority="EPFO",
		source="EPF Scheme, para 38",
	),
	obligation(
		"ESI Contribution",
		"ESI",
		"Monthly Contribution",
		"Monthly",
		1,
		15,
		registration="ESI",
		payment=1,
		authority="ESIC",
		source="ESI (Central) Regulations, reg. 31",
	),
	after_agm("AOC-4 (Financial Statements)", "AOC-4", 30, "Companies Act s.137"),
	after_agm("MGT-7 / MGT-7A (Annual Return)", "MGT-7", 60, "Companies Act s.92"),
	after_agm("ADT-1 (Auditor Appointment)", "ADT-1", 15, "Companies Act s.139"),
	obligation(
		"DIR-3 KYC",
		"Companies Act",
		"DIR-3 KYC",
		"Yearly",
		6,
		30,
		companies=COMPANIES,
		authority="Registrar of Companies",
		source="Companies (Appointment and Qualification of Directors) Rules, rule 12A",
	),
	obligation(
		"DPT-3 (Return of Deposits)",
		"Companies Act",
		"DPT-3",
		"Yearly",
		3,
		30,
		companies=COMPANIES,
		authority="Registrar of Companies",
		source="Companies (Acceptance of Deposits) Rules, rule 16",
	),
	obligation(
		"MSME-1 (Dues to MSMEs)",
		"Companies Act",
		"MSME-1",
		"Half-yearly",
		1,
		31,
		companies=COMPANIES,
		default=0,
		authority="Registrar of Companies",
		source="Companies Act s.405 order",
	),
	obligation(
		"LLP Form 11 (Annual Return)",
		"LLP Act",
		"Form 11",
		"Yearly",
		2,
		30,
		companies=["LLP"],
		authority="Registrar of Companies",
		source="LLP Act s.35",
	),
	obligation(
		"LLP Form 8 (Statement of Account)",
		"LLP Act",
		"Form 8",
		"Yearly",
		7,
		30,
		companies=["LLP"],
		authority="Registrar of Companies",
		source="LLP Act s.34",
	),
	state_tax("Professional Tax", "Karnataka", "Monthly", 1, 20, "PT"),
	state_tax("Professional Tax", "Maharashtra", "Monthly", 0, 31, "PT"),
	state_tax("Professional Tax", "Tamil Nadu", "Half-yearly", 0, 31, "PT"),
	state_tax("Professional Tax", "Telangana", "Monthly", 1, 10, "PT"),
	state_tax("Professional Tax", "West Bengal", "Monthly", 1, 21, "PT"),
	state_tax("Professional Tax", "Gujarat", "Monthly", 1, 15, "PT"),
	state_tax("Labour Welfare Fund", "Karnataka", "Yearly", 1, 15, "LWF", "Calendar Year"),
	state_tax("Labour Welfare Fund", "Maharashtra", "Half-yearly", 1, 15, "LWF", "Calendar Year"),
	state_tax("Labour Welfare Fund", "Tamil Nadu", "Yearly", 1, 31, "LWF", "Calendar Year"),
	state_tax("Labour Welfare Fund", "Telangana", "Yearly", 1, 31, "LWF", "Calendar Year"),
	state_tax("Labour Welfare Fund", "West Bengal", "Half-yearly", 1, 15, "LWF", "Calendar Year"),
	state_tax("Labour Welfare Fund", "Gujarat", "Half-yearly", 1, 31, "LWF", "Calendar Year"),
]

CLIENT_OWNED_FIELDS = ("is_active",)


def sync_standard_templates():
	"""Create or update every standard template from LIBRARY. Safe to run on every migrate."""
	for values in LIBRARY:
		name = values["template_name"]
		if frappe.db.exists("Compliance Obligation Template", name):
			doc = frappe.get_doc("Compliance Obligation Template", name)
			for fieldname in CLIENT_OWNED_FIELDS:
				values = {**values, fieldname: doc.get(fieldname)}
			# update() replaces child tables wholesale, so rows dropped from LIBRARY go too.
			doc.update({key: value for key, value in values.items() if key != "template_name"})
		else:
			doc = frappe.get_doc({"doctype": "Compliance Obligation Template", **values})
		doc.is_standard = 1
		doc.flags.ignore_permissions = True  # the app's own library, written during migrate
		doc.save()
