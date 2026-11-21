# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""What filing late costs, for the standard obligation templates.

These are the figures the penalty estimate uses: a late fee per day, a one-off late fee, a
cap, whether the fee is capped at the tax, and interest a year on tax paid late. Fines that
depend on an officer's judgement or a turnover slab are not counted; the rule in words says
so. Every figure is taken from the Act or notification named, and stays marked as not checked
(penalty_checked_on empty) until a chartered accountant has confirmed it. A firm that reckons
differently keeps its own figures apart (penalty_figures.py), so updates never touch them.
"""

GST_RETURN = (
	"Late fee under s.47 of the CGST Act and the matching SGST Act: ₹50 a day (₹20 for a nil "
	"return), capped by the previous year's turnover at ₹2,000, ₹5,000 or ₹10,000, and at ₹500 "
	"for a nil return (Notifications 19/2021 and 20/2021-Central Tax). The estimate uses ₹50 a "
	"day and the highest cap, or ₹20 a day and ₹500 for a filing marked NIL."
)
GST_INTEREST = "Interest at 18% a year on tax paid late, under s.50 of the CGST Act."
TDS_RETURN = (
	"Late fee under s.234E of the Income-tax Act: ₹200 a day, up to the tax deducted or "
	"collected. A penalty of ₹10,000 to ₹1,00,000 under s.271H is possible after a year; the "
	"estimate does not count it."
)
ROC_PER_DAY = (
	"Additional fee of ₹100 a day of delay, with no cap (Companies (Registration Offices and "
	"Fees) Rules, 2014, as amended in 2018)."
)
ROC_SLAB = (
	"Additional fee in slabs of 2 to 12 times the normal filing fee, by length of delay "
	"(Companies (Registration Offices and Fees) Rules, 2014). The estimate cannot count it, "
	"as the normal fee depends on the company's capital."
)
LLP_PER_DAY = "Additional fee of ₹100 a day of delay, with no cap (LLP (Second Amendment) Rules, 2022)."
ITR = (
	"Late fee of ₹5,000 under s.234F (₹1,000 if total income is up to ₹5 lakh), and interest "
	"of 1% a month on tax unpaid under s.234A."
)
TAX_AUDIT = (
	"Penalty under s.271B of 0.5% of turnover, at most ₹1,50,000, which the officer may levy. "
	"The estimate does not count it."
)
PF = (
	"Damages of 5% to 25% a year by length of delay (s.14B of the EPF Act), and interest at "
	"12% a year (s.7Q). The estimate counts the interest only."
)
ESI = (
	"Interest at 12% a year on contributions paid late (Regulation 31A), and damages of 5% "
	"to 25% a year (Regulation 31C). The estimate counts the interest only."
)
STATE_RULE = (
	"Interest and penalties under the state's own Act differ by state; the estimate does not "
	"count them. Add the state's figures and tick Set by Us."
)
LODR = (
	"Fine under SEBI's standard operating procedure for listing regulations (circular of "
	"22 January 2020, as amended): {0} a day of delay. The exchange may levy more for repeated "
	"delays."
)

GST_3B = dict(
	late_fee_per_day=50, late_fee_cap=10000, interest_percent=18, penalty_rule=GST_RETURN + " " + GST_INTEREST
)
GST_1 = dict(late_fee_per_day=50, late_fee_cap=10000, penalty_rule=GST_RETURN)
TDS = dict(late_fee_per_day=200, cap_at_tax=1, penalty_rule=TDS_RETURN)

PENALTIES = {
	"GSTR-1 (Monthly)": GST_1,
	"GSTR-1 (QRMP)": GST_1,
	"GSTR-3B (Monthly)": GST_3B,
	"GSTR-3B (QRMP, 22nd)": GST_3B,
	"GSTR-3B (QRMP, 24th)": GST_3B,
	"GSTR-9 (Annual Return)": dict(
		late_fee_per_day=200,
		penalty_rule=(
			"Late fee under s.47: ₹50 to ₹200 a day by turnover, capped at 0.04% to 0.5% of "
			"turnover (Notification 07/2023-Central Tax). The estimate uses ₹200 a day without a cap."
		),
	),
	"GSTR-9C (Reconciliation)": dict(
		penalty_rule="Filed with GSTR-9; its late fee is counted on GSTR-9 (Notification 30/2021-Central Tax)."
	),
	"PMT-06 (QRMP Monthly Payment)": dict(interest_percent=18, penalty_rule="No late fee. " + GST_INTEREST),
	"CMP-08 (Composition Payment)": dict(interest_percent=18, penalty_rule="No late fee. " + GST_INTEREST),
	"GSTR-4 (Composition Annual Return)": dict(
		late_fee_per_day=50,
		late_fee_cap=2000,
		penalty_rule=(
			"Late fee under s.47: ₹50 a day (₹20 for a nil return), at most ₹2,000 (₹500 for a "
			"nil return) (Notification 07/2023-Central Tax)."
		),
	),
	"ITC-04 (Job Work, turnover above ₹5 crore)": dict(
		penalty_rule="No late fee; a general penalty of up to ₹25,000 under s.125 is possible. Not counted."
	),
	"ITC-04 (Job Work, turnover up to ₹5 crore)": dict(
		penalty_rule="No late fee; a general penalty of up to ₹25,000 under s.125 is possible. Not counted."
	),
	"TDS/TCS Payment": dict(
		interest_percent=18,
		penalty_rule="Interest of 1.5% a month on tax deposited late, under s.201(1A) and s.206C(7).",
	),
	"TDS Return 24Q (Salary)": TDS,
	"TDS Return 26Q (Non-salary)": TDS,
	"TDS Return 27Q (Non-residents)": TDS,
	"TCS Return 27EQ": TDS,
	"Form 16A": dict(
		late_fee_per_day=100,
		cap_at_tax=1,
		penalty_rule="Penalty under s.272A(2)(g): ₹100 a day, up to the tax deducted.",
	),
	"Form 16": dict(
		late_fee_per_day=100,
		cap_at_tax=1,
		penalty_rule="Penalty under s.272A(2)(g): ₹100 a day, up to the tax deducted.",
	),
	"Advance Tax": dict(
		interest_percent=12,
		penalty_rule="Interest of 1% a month on the shortfall, under s.234B and s.234C.",
	),
	"Tax Audit Report": dict(penalty_rule=TAX_AUDIT),
	"Tax Audit Report (Firms and Proprietors)": dict(penalty_rule=TAX_AUDIT),
	"Income Tax Return (Audit Cases)": dict(late_fee_flat=5000, interest_percent=12, penalty_rule=ITR),
	"Income Tax Return (Firms, Non-audit)": dict(late_fee_flat=5000, interest_percent=12, penalty_rule=ITR),
	"Income Tax Return (Firms, Audit Cases)": dict(late_fee_flat=5000, interest_percent=12, penalty_rule=ITR),
	"Income Tax Return (Proprietor, Non-audit)": dict(
		late_fee_flat=5000, interest_percent=12, penalty_rule=ITR
	),
	"Income Tax Return (Proprietor, Audit Cases)": dict(
		late_fee_flat=5000, interest_percent=12, penalty_rule=ITR
	),
	"PF ECR and Payment": dict(interest_percent=12, penalty_rule=PF),
	"ESI Contribution": dict(interest_percent=12, penalty_rule=ESI),
	"AOC-4 (Financial Statements)": dict(late_fee_per_day=100, penalty_rule=ROC_PER_DAY),
	"MGT-7 / MGT-7A (Annual Return)": dict(late_fee_per_day=100, penalty_rule=ROC_PER_DAY),
	"ADT-1 (Auditor Appointment)": dict(penalty_rule=ROC_SLAB),
	"DIR-3 KYC": dict(
		late_fee_flat=5000,
		penalty_rule="Fee of ₹5,000 to file after the due date, and the DIN is deactivated until then (Rule 12A).",
	),
	"DPT-3 (Return of Deposits)": dict(penalty_rule=ROC_SLAB),
	"MSME-1 (Dues to MSMEs)": dict(
		penalty_rule="Penalty under s.405(4) of up to ₹25,000 on the company, which the Registrar may levy. Not counted."
	),
	"LLP Form 11 (Annual Return)": dict(late_fee_per_day=100, penalty_rule=LLP_PER_DAY),
	"LLP Form 8 (Statement of Account)": dict(late_fee_per_day=100, penalty_rule=LLP_PER_DAY),
	"LLP Form 3 (LLP Agreement Changed)": dict(late_fee_per_day=100, penalty_rule=LLP_PER_DAY),
	"LLP Form 4 (Partner Changed)": dict(late_fee_per_day=100, penalty_rule=LLP_PER_DAY),
	"INC-20A (Commencement of Business)": dict(
		late_fee_flat=50000,
		penalty_rule="Penalty of ₹50,000 on the company under s.10A, and ₹1,000 a day on officers (not counted).",
	),
	"FSSAI Annual Return (D-1)": dict(
		late_fee_per_day=100,
		penalty_rule="Late fee of ₹100 a day (Food Safety and Standards (Licensing) Regulations, 2.1.13).",
	),
	"Shareholding Pattern": dict(late_fee_per_day=2000, penalty_rule=LODR.format("₹2,000")),
	"Integrated Filing (Governance)": dict(late_fee_per_day=2000, penalty_rule=LODR.format("₹2,000")),
	"Integrated Filing (Financial)": dict(late_fee_per_day=5000, penalty_rule=LODR.format("₹5,000")),
	"Annual Secretarial Compliance Report": dict(late_fee_per_day=2000, penalty_rule=LODR.format("₹2,000")),
}
# A late NIL return: ₹20 a day (₹10 CGST and ₹10 SGST, Notification 76/2018-Central Tax), at most
# ₹500 a return (Notifications 19/2021, 20/2021 and 21/2021-Central Tax). Returns not listed cost
# nothing when NIL: no fee is set for them, or it is capped at the tax, which is nil.
NIL_GST = dict(nil_late_fee_per_day=20, nil_late_fee_cap=500)
NIL_PENALTIES = {
	"GSTR-1 (Monthly)": NIL_GST,
	"GSTR-1 (QRMP)": NIL_GST,
	"GSTR-3B (Monthly)": NIL_GST,
	"GSTR-3B (QRMP, 22nd)": NIL_GST,
	"GSTR-3B (QRMP, 24th)": NIL_GST,
	"GSTR-4 (Composition Annual Return)": NIL_GST,
}
NIL_FIELDS = ("nil_late_fee_flat", "nil_late_fee_per_day", "nil_late_fee_cap")
# Event forms, state taxes and the rest share these words when they have no figures of their own.
EVENT_FORM_RULE = ROC_SLAB
FIELDS = (
	"late_fee_per_day",
	"late_fee_flat",
	"late_fee_cap",
	"cap_at_tax",
	"interest_percent",
	"penalty_rule",
)


def penalty_of(template: dict) -> dict:
	"""The late-filing figures for a standard template, empty where the law gives none."""
	figures = PENALTIES.get(template["template_name"])
	if figures is None:
		if template.get("event_type") and template.get("law") == "Companies Act":
			figures = {"penalty_rule": EVENT_FORM_RULE}
		elif template.get("law") in ("Professional Tax", "Labour Welfare Fund"):
			figures = {"penalty_rule": STATE_RULE}
		else:
			figures = {}
	return {field: figures.get(field, 0 if field != "penalty_rule" else None) for field in FIELDS}


def nil_penalty_of(template: dict) -> dict:
	"""What filing a NIL return late costs, for a standard template; nothing where no figure is set."""
	figures = NIL_PENALTIES.get(template["template_name"], {})
	return {field: figures.get(field, 0) for field in NIL_FIELDS}
