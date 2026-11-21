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

from kxcompliance import scoped
from kxcompliance.kx_compliance.penalty_library import nil_penalty_of, penalty_of

COMPANIES = ["Private Limited", "Public Limited", "One Person Company"]
FIRMS = ["LLP", "Partnership"]
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
		"event_type": None,
		"overrides": [
			{"period_end_month": month, "months_after_period": after, "due_day": due_day}
			for month, after, due_day in extra.pop("overrides", ())
		],
		"company_types": [{"company_type": kind} for kind in extra.pop("companies", ())],
		"registration_type": extra.pop("registration", None),
		"states": "\n".join(extra.pop("states", ())),
		"skip_months": ", ".join(str(month) for month in extra.pop("skip_months", ())),
		"add_by_default": extra.pop("default", 1),
		"requires_payment": extra.pop("payment", 0),
		"requires_proof": 1,
		"requires_review": 1,
		"allows_nil": extra.pop("nil", 0),
		"nil_needs_acknowledgement": extra.pop("nil_ack", 1),
		"files_in_order": extra.pop("in_order", 0),
		"filed_after_form": extra.pop("after_form", None),
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


def after_event(name, form, event_type, days, source, law="Companies Act", companies=COMPANIES):
	"""A form due a set number of days after a company event, made when the event is recorded."""
	values = obligation(
		name, law, form, "Per Event", companies=companies, authority="Registrar of Companies", source=source
	)
	values.update(
		{
			"due_after_event": 1,
			"days_after_event": days,
			"event_type": event_type,
			"months_after_period": None,
			"due_day": None,
		}
	)
	return values


# The events the shipped event-based forms follow, with what each covers.
EVENT_TYPES = {
	"Incorporation": "The company was incorporated.",
	"Change in Directors": "A director was appointed, resigned, left or changed designation.",
	"Resolution to be Filed": "A special resolution, or another resolution section 117 requires to be filed.",
	"Shares Allotted (Private Placement)": "Shares or securities allotted on a private placement.",
	"Shares Allotted (Other)": "Shares allotted otherwise, such as on a rights or bonus issue.",
	"Authorised Capital Changed": "The authorised share capital was increased, consolidated or otherwise altered.",
	"Charge Created or Modified": "A charge on the company's assets was created or modified.",
	"Charge Satisfied": "A registered charge was paid off in full.",
	"Registered Office Moved": "The registered office moved within the same city, town or village.",
	"Beneficial Ownership Declared": "A declaration of significant beneficial ownership (BEN-1) was received.",
	"LLP Agreement Changed": "The LLP agreement was changed.",
	"Partner Changed": "A partner or designated partner joined, left or changed.",
}


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
		nil=int(law == "Professional Tax"),
		source=f"{state} {law} rules; confirm the current due date before release.",
	)


GST = dict(registration="GST", authority="GST Network")
COMPOSITION = dict(registration="GST Composition", authority="GST Network")
LISTED = dict(registration="Stock Exchange", authority="Stock Exchanges", companies=["Public Limited"])
# Income-tax Act, 2025 applies from 1 April 2026. Finance Act 2026 moved non-audit business
# returns (firms and proprietors) to 31 August; confirm against CBDT before each release.
INCOME_TAX_2025 = "Income-tax Act, 2025, return of income; Finance Act 2026 for the non-audit date"
TAN = dict(registration="TAN", authority="Income Tax Department")
# GST returns are filed NIL with an ARN (on the portal or by SMS to 14409), one period after the
# other: the portal refuses a period while an earlier one is unfiled (CGST Act s.39(10)).
NIL_IN_ORDER = dict(nil=1, in_order=1)
# A quarter with no TDS needs no statement: TRACES takes a "Declaration for non-filing", which
# gives no acknowledgement number. A month with no TDS has no challan to pay.
NIL_DECLARED = dict(nil=1, nil_ack=0)

LIBRARY = [
	obligation(
		"GSTR-1 (Monthly)", "GST", "GSTR-1", "Monthly", 1, 11, source="CGST Act s.37", **GST, **NIL_IN_ORDER
	),
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
		**NIL_IN_ORDER,
	),
	# GSTR-3B for a period cannot be filed until that period's GSTR-1 is (CGST Act s.39(10), as
	# amended by the Finance Act 2022); the portal enforces it.
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
		after_form="GSTR-1",
		**NIL_IN_ORDER,
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
		after_form="GSTR-1",
		**NIL_IN_ORDER,
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
		after_form="GSTR-1",
		**NIL_IN_ORDER,
	),
	# QRMP: tax for the first two months of a quarter is paid by the 25th of the next month; the
	# third month's is paid with the quarter's GSTR-3B. A month with nothing to pay needs no challan.
	obligation(
		"PMT-06 (QRMP Monthly Payment)",
		"GST",
		"PMT-06",
		"Monthly",
		1,
		25,
		skip_months=(3, 6, 9, 12),
		payment=1,
		default=0,
		source="CGST Act s.39(7) proviso; CGST rule 61(1), QRMP scheme (Notification 85/2020-Central Tax)",
		**GST,
		**NIL_DECLARED,
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
		**NIL_DECLARED,
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
		**NIL_DECLARED,
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
		**NIL_DECLARED,
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
		**NIL_DECLARED,
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
		nil=1,
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
		nil=1,
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
	# Added 15 Nov 2026 where recent sources agree; checked_on stays empty for the CA.
	state_tax("Professional Tax", "Andhra Pradesh", "Monthly", 1, 10, "PT"),
	state_tax("Professional Tax", "Assam", "Monthly", 1, 28, "PT"),
	state_tax("Labour Welfare Fund", "Andhra Pradesh", "Yearly", 1, 31, "LWF", "Calendar Year"),
	state_tax("Labour Welfare Fund", "Delhi", "Half-yearly", 1, 15, "LWF", "Calendar Year"),
	state_tax("Labour Welfare Fund", "Madhya Pradesh", "Half-yearly", 1, 15, "LWF", "Calendar Year"),
	state_tax("Labour Welfare Fund", "Chhattisgarh", "Half-yearly", 1, 15, "LWF", "Calendar Year"),
	state_tax("Labour Welfare Fund", "Odisha", "Half-yearly", 1, 15, "LWF", "Calendar Year"),
	state_tax("Labour Welfare Fund", "Punjab", "Half-yearly", 1, 15, "LWF"),
	state_tax("Labour Welfare Fund", "Chandigarh", "Half-yearly", 1, 15, "LWF"),
	# Income tax for firms and proprietors: non-audit returns are added by default; a business
	# that needs a tax audit switches to the audit-case templates.
	obligation(
		"Income Tax Return (Firms, Non-audit)",
		"Income Tax",
		"ITR-5",
		"Yearly",
		5,
		31,
		companies=FIRMS,
		payment=1,
		authority="Income Tax Department",
		source=INCOME_TAX_2025,
	),
	obligation(
		"Income Tax Return (Firms, Audit Cases)",
		"Income Tax",
		"ITR-5",
		"Yearly",
		7,
		31,
		companies=FIRMS,
		payment=1,
		default=0,
		authority="Income Tax Department",
		source=INCOME_TAX_2025,
	),
	obligation(
		"Income Tax Return (Proprietor, Non-audit)",
		"Income Tax",
		"ITR-3 / ITR-4",
		"Yearly",
		5,
		31,
		companies=["Proprietorship"],
		payment=1,
		authority="Income Tax Department",
		source=INCOME_TAX_2025,
	),
	obligation(
		"Income Tax Return (Proprietor, Audit Cases)",
		"Income Tax",
		"ITR-3",
		"Yearly",
		7,
		31,
		companies=["Proprietorship"],
		payment=1,
		default=0,
		authority="Income Tax Department",
		source=INCOME_TAX_2025,
	),
	obligation(
		"Tax Audit Report (Firms and Proprietors)",
		"Income Tax",
		"Tax audit report",
		"Yearly",
		6,
		30,
		companies=[*FIRMS, "Proprietorship"],
		default=0,
		authority="Income Tax Department",
		source="Income-tax Act, 2025, tax audit",
	),
	obligation(
		"TDS Return 27Q (Non-residents)",
		"TDS/TCS",
		"27Q",
		"Quarterly",
		1,
		31,
		overrides=[(3, 2, 31)],
		default=0,
		source="Income-tax Rules, quarterly TDS statement for payments to non-residents",
		**TAN,
		**NIL_DECLARED,
	),
	# GST composition: a taxpayer under the scheme records its GSTIN as "GST Composition", so
	# GSTR-1, GSTR-3B and GSTR-9 do not apply to it.
	obligation(
		"CMP-08 (Composition Payment)",
		"GST",
		"CMP-08",
		"Quarterly",
		1,
		18,
		payment=1,
		source="CGST rule 62",
		**COMPOSITION,
		nil=1,
	),
	obligation(
		"GSTR-4 (Composition Annual Return)",
		"GST",
		"GSTR-4",
		"Yearly",
		3,
		30,
		source="CGST rule 62; due 30 June from FY 2024-25 (Notification 12/2024)",
		**COMPOSITION,
		nil=1,
	),
	obligation(
		"ITC-04 (Job Work, turnover above ₹5 crore)",
		"GST",
		"ITC-04",
		"Half-yearly",
		1,
		25,
		default=0,
		source="CGST rule 45(3); confirm the current turnover limits",
		**GST,
	),
	obligation(
		"ITC-04 (Job Work, turnover up to ₹5 crore)",
		"GST",
		"ITC-04",
		"Yearly",
		1,
		25,
		default=0,
		source="CGST rule 45(3); confirm the current turnover limits",
		**GST,
	),
	# Foreign trade and investment, food businesses.
	obligation(
		"FLA Return (Foreign Liabilities and Assets)",
		"FEMA",
		"FLA",
		"Yearly",
		4,
		15,
		companies=[*COMPANIES, "LLP"],
		default=0,
		authority="Reserve Bank of India",
		source="FEMA; RBI annual return on foreign liabilities and assets, due 15 July",
	),
	obligation(
		"IEC Annual Update",
		"Foreign Trade Policy",
		"IEC update",
		"Yearly",
		3,
		30,
		registration="IEC",
		authority="DGFT",
		source="Foreign Trade Policy, para 2.13; update every April to June",
	),
	obligation(
		"FSSAI Annual Return (D-1)",
		"Food Safety",
		"D-1",
		"Yearly",
		2,
		31,
		registration="FSSAI",
		default=0,
		authority="FSSAI",
		source="FSS (Licensing and Registration) Regulations; manufacturers and importers, due 31 May",
	),
	# Listed companies (SEBI LODR), for a company that records its listing as "Stock Exchange".
	obligation(
		"Shareholding Pattern",
		"SEBI LODR",
		"Shareholding pattern",
		"Quarterly",
		1,
		21,
		source="SEBI LODR reg. 31(1)(b)",
		**LISTED,
	),
	obligation(
		"Integrated Filing (Governance)",
		"SEBI LODR",
		"Integrated filing - governance",
		"Quarterly",
		1,
		30,
		source="SEBI circular of 31 Dec 2024; includes reg. 13(3) and 27(2)(a)",
		**LISTED,
	),
	obligation(
		"Integrated Filing (Financial)",
		"SEBI LODR",
		"Integrated filing - financial",
		"Quarterly",
		2,
		14,
		overrides=[(3, 2, 30)],
		source="SEBI circular of 31 Dec 2024; reg. 33: 45 days, 60 days for the last quarter",
		**LISTED,
	),
	obligation(
		"Reconciliation of Share Capital Audit",
		"SEBI LODR",
		"Reg 76 report",
		"Quarterly",
		1,
		30,
		source="SEBI (Depositories and Participants) Regulations, reg. 76",
		**LISTED,
	),
	obligation(
		"Annual Secretarial Compliance Report",
		"SEBI LODR",
		"Reg 24A report",
		"Yearly",
		2,
		30,
		source="SEBI LODR reg. 24A",
		**LISTED,
	),
	# Forms due after a company event (recorded as a Compliance Event).
	after_event("INC-20A (Commencement of Business)", "INC-20A", "Incorporation", 180, "Companies Act s.10A"),
	after_event(
		"DIR-12 (Change in Directors)", "DIR-12", "Change in Directors", 30, "Companies Act s.170(2)"
	),
	after_event(
		"MGT-14 (Filing of Resolutions)", "MGT-14", "Resolution to be Filed", 30, "Companies Act s.117"
	),
	after_event(
		"PAS-3 (Allotment, Private Placement)",
		"PAS-3",
		"Shares Allotted (Private Placement)",
		15,
		"Companies Act s.42(9)",
	),
	after_event("PAS-3 (Allotment, Other)", "PAS-3", "Shares Allotted (Other)", 30, "Companies Act s.39(4)"),
	after_event(
		"SH-7 (Alteration of Capital)", "SH-7", "Authorised Capital Changed", 30, "Companies Act s.64"
	),
	after_event(
		"CHG-1 (Charge Created or Modified)", "CHG-1", "Charge Created or Modified", 30, "Companies Act s.77"
	),
	after_event("CHG-4 (Charge Satisfied)", "CHG-4", "Charge Satisfied", 30, "Companies Act s.82"),
	after_event(
		"INC-22 (Registered Office Moved)",
		"INC-22",
		"Registered Office Moved",
		15,
		"Companies Act s.12(4); sources give 15 or 30 days, so the earlier is used until confirmed",
	),
	after_event(
		"BEN-2 (Significant Beneficial Owner)",
		"BEN-2",
		"Beneficial Ownership Declared",
		30,
		"Companies Act s.90; Significant Beneficial Owners Rules, rule 4",
	),
	after_event(
		"LLP Form 3 (LLP Agreement Changed)",
		"Form 3",
		"LLP Agreement Changed",
		30,
		"LLP Act s.23; LLP Rules, rule 21",
		law="LLP Act",
		companies=["LLP"],
	),
	after_event(
		"LLP Form 4 (Partner Changed)",
		"Form 4",
		"Partner Changed",
		30,
		"LLP Act s.25; LLP Rules, rule 22",
		law="LLP Act",
		companies=["LLP"],
	),
]

CLIENT_OWNED_FIELDS = ("is_active",)


def sync_standard_event_types():
	for name, description in EVENT_TYPES.items():
		if scoped.exists("Compliance Event Type", name):
			doc = frappe.get_doc("Compliance Event Type", name)
		else:
			doc = frappe.new_doc("Compliance Event Type")
			doc.event_type_name = name
		doc.description = description
		doc.is_standard = 1
		doc.flags.ignore_permissions = True  # the app's own list, written during migrate
		doc.save()


def sync_standard_templates():
	"""Create or update every standard template from LIBRARY. Safe to run on every migrate."""
	sync_standard_event_types()
	for values in LIBRARY:
		name = values["template_name"]
		values = {**values, **penalty_of(values), **nil_penalty_of(values)}
		if scoped.exists("Compliance Obligation Template", name):
			doc = frappe.get_doc("Compliance Obligation Template", name)
			for fieldname in CLIENT_OWNED_FIELDS:
				values = {**values, fieldname: doc.get(fieldname)}
			# update() replaces child tables wholesale, so rows dropped from LIBRARY go too.
			doc.update({key: value for key, value in values.items() if key != "template_name"})
		else:
			doc = frappe.get_doc({"doctype": "Compliance Obligation Template", **values})
		doc.is_standard = 1
		doc.flags.from_library = True
		doc.flags.ignore_permissions = True  # the app's own library, written during migrate
		doc.save()
