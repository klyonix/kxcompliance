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

export const TYPE_VIEWS = [
	{ label: "In use", value: "active" },
	{ label: "Off", value: "off" },
	{ label: "All", value: "all" },
];

// The item types list's columns (RowList cells); a type has no date of its own.
export const TYPE_COLUMNS = [{ label: "Category" }, { label: "Renews" }];

// The types in a tab whose names have every word typed.
export function typesShown(types, view, search = "") {
	const words = search.toLowerCase().split(/\s+/).filter(Boolean);
	return (types || []).filter((type) => {
		if (view === "active" && !type.is_active) return false;
		if (view === "off" && type.is_active) return false;
		const name = type.name.toLowerCase();
		return words.every((word) => name.includes(word));
	});
}

export function typeEmpty(view, searching) {
	if (searching) return { title: "No matches", detail: "Try another name, or look under All." };
	if (view === "off")
		return { title: "No type is switched off", detail: "Types you stop using appear here." };
	return {
		title: "No item types yet",
		detail: "Add the kinds of licence, registration and certificate you keep.",
		action: "Add a type",
	};
}

export const renewsText = (type) =>
	type.renewal_cycle_months ? `Every ${type.renewal_cycle_months} months` : "Does not expire";

export function typeRow(type) {
	return {
		key: type.name,
		kind: "item-type",
		title: type.name,
		detail: type.set_by_firm ? `${typeSummary(type)} · your own settings` : typeSummary(type),
		status: type.is_active ? "In use" : "Off",
		theme: type.is_active ? "green" : "gray",
		cells: [type.category, renewsText(type)],
		due: { text: "", late: false },
		to: { name: "ItemType", params: { name: type.name } },
	};
}
