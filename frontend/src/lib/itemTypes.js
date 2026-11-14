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
