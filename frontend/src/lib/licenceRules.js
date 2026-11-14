// Licence rules: which licences a customer or supplier must hold before a sale or purchase, and
// the documents a rule was checked on (blocks, warnings and the ones let through once).

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

// The Desk page of a selling or buying document, where it is finished once let through.
export const documentLink = (doctype, name) =>
	`/app/${doctype.toLowerCase().replace(/ /g, "-")}/${encodeURIComponent(name)}`;
