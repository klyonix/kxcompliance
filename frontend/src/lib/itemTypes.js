// Register item types: their reminder days written as a list a person can type.

export const CATEGORIES = [
	"Licence",
	"Registration",
	"Certificate",
	"Insurance",
	"Subscription",
	"Contract",
];

// "60, 30, 7" → [60, 30, 7]: whole days, largest first, each once.
export function parseDays(text) {
	const days = String(text || "")
		.split(/[\s,;]+/)
		.filter((part) => part !== "")
		.map((part) => Number(part))
		.filter((day) => Number.isInteger(day) && day >= 0);
	return [...new Set(days)].sort((a, b) => b - a);
}

export const daysText = (rules) =>
	rules
		.map((rule) => rule.days_before)
		.sort((a, b) => b - a)
		.join(", ");

export function typeSummary(type) {
	const parts = [type.category];
	parts.push(
		type.renewal_cycle_months
			? `renews every ${type.renewal_cycle_months} months`
			: "does not expire"
	);
	if (type.requires_document) parts.push("certificate needed");
	return parts.join(" · ");
}

export const TYPE_FIELDS = [
	"name",
	"category",
	"renewal_cycle_months",
	"requires_document",
	"is_active",
];

export const TYPE_VIEWS = [
	{ label: "In use", value: "active", filters: [["is_active", "=", 1]], orderBy: "name asc" },
	{ label: "Off", value: "off", filters: [["is_active", "=", 0]], orderBy: "name asc" },
	{ label: "All", value: "all", filters: [], orderBy: "name asc" },
];

// The item types list's columns (RecordList); a type has no date of its own.
export const TYPE_LIST = {
	columns: [
		{ label: "Category", field: "category" },
		{ label: "Renews", value: (type) => renewsText(type) },
	],
	dateLabel: null,
};

export const renewsText = (type) =>
	type.renewal_cycle_months ? `Every ${type.renewal_cycle_months} months` : "Does not expire";

export function typeRow(type) {
	return {
		key: type.name,
		kind: "item-type",
		title: type.name,
		detail: typeSummary(type),
		status: type.is_active ? "In use" : "Off",
		theme: type.is_active ? "green" : "gray",
		due: { text: "", late: false },
		to: { name: "ItemType", params: { name: type.name } },
	};
}
