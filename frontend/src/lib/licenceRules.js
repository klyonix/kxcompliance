// Licence rules: which licences a customer or supplier must hold before a sale or purchase, and
// the documents a rule was checked on (blocks, warnings and the ones let through once).
import { deskRoute } from "@/navigation";

export const CHECK_FIELDS = [
	"check_quotation",
	"check_sales_order",
	"check_delivery_note",
	"check_sales_invoice",
	"check_purchase_order",
	"check_purchase_receipt",
	"check_purchase_invoice",
];

export const RULE_FIELDS = [
	"name",
	"item_type",
	"party_type",
	"action",
	"is_active",
	"grace_days",
	...CHECK_FIELDS,
];

// "Customers need FSSAI Licence · blocks Sales Order, Sales Invoice"
export function ruleSummary(rule, documents) {
	const checked = documents
		.filter((document) => document.party_type === rule.party_type && rule[document.field])
		.map((document) => document.doctype);
	const who = rule.party_type === "Supplier" ? "Suppliers" : "Customers";
	const verb = rule.action === "Block" ? "blocks" : "warns on";
	return checked.length
		? `${who} need it · ${verb} ${checked.join(", ")}`
		: `${who} need it · checked on no document yet`;
}

export const CHECK_VIEWS = [
	{ label: "Blocked", value: "blocked", result: "Blocked" },
	{ label: "Warned", value: "warned", result: "Warned" },
	{ label: "Let through", value: "allowed", result: "Overridden" },
];

export const overrideKey = (doctype, name) => `${doctype}|${name}`;

// One row per document, the latest check first: a document checked several times as it was
// edited shows once.
export function latestPerDocument(logs) {
	const seen = new Set();
	return logs.filter((log) => {
		const key = overrideKey(log.reference_doctype, log.reference_name);
		if (seen.has(key)) return false;
		seen.add(key);
		return true;
	});
}

// One selling or buying document a rule was checked on (RowList); it opens in the Desk, where it
// is finished once let through. An older block of a document that was never saved has no name:
// there is nothing to open or allow. `allowed` says whether a manager let it through once; `checkedBy`
// and `checkedOn` are the person's name and the time, written for reading.
export function checkRow(log, { allowed, checkedBy, checkedOn = "" }) {
	return {
		key: log.name,
		kind: "licence-check",
		title: log.reference_name
			? `${log.reference_doctype} ${log.reference_name}`
			: `${log.reference_doctype} (not saved)`,
		detail: [log.message, log.item_type].filter(Boolean).join(" · "),
		status: allowed ? "Let through" : log.result,
		theme: allowed ? "green" : log.result === "Blocked" ? "red" : "amber",
		due: { text: checkedOn, late: false },
		cells: [log.party, checkedBy],
		href: log.reference_name ? deskRoute(log.reference_doctype, log.reference_name) : "",
		log,
		allowed,
	};
}

export const RULE_VIEWS = [
	{
		label: "In use",
		value: "active",
		filters: [["is_active", "=", 1]],
		orderBy: "item_type asc",
	},
	{ label: "Off", value: "off", filters: [["is_active", "=", 0]], orderBy: "item_type asc" },
	{ label: "All", value: "all", filters: [], orderBy: "item_type asc" },
];

// The licence rules list's columns (RecordList); a rule has no date of its own.
export const RULE_LIST = {
	nameLabel: "Licence",
	columns: [
		{
			label: "Who must hold it",
			value: (rule) => (rule.party_type === "Supplier" ? "Suppliers" : "Customers"),
		},
	],
	dateLabel: null,
};

// `documents` are the selling and buying documents a rule can check (licence_rule_options).
export function ruleRow(rule, documents) {
	return {
		key: rule.name,
		kind: "licence-rule",
		title: rule.item_type,
		detail: ruleSummary(rule, documents),
		status: rule.is_active ? rule.action : "Off",
		theme: !rule.is_active ? "gray" : rule.action === "Block" ? "red" : "amber",
		due: { text: "", late: false },
		to: { name: "LicenceRule", params: { name: rule.name } },
	};
}
