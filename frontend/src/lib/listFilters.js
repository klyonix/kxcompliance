// "Exactly these records": a list opened from an Overview number carries that number's filters in
// the address, so the list shows what was counted. Read back with care, as anyone can edit an
// address: only a list of [field, operator, value] with a known operator is used; the server
// still applies the person's permissions to whatever is asked.
const OPERATORS = ["=", "!=", "in", "not in", "between", "<", ">", "<=", ">=", "is"];

export function parseListFilters(text) {
	if (typeof text !== "string" || !text) return null;
	try {
		const filters = JSON.parse(text);
		const valid =
			Array.isArray(filters) &&
			filters.length > 0 &&
			filters.every(
				(filter) =>
					Array.isArray(filter) &&
					filter.length === 3 &&
					typeof filter[0] === "string" &&
					/^[a-z_]+$/.test(filter[0]) &&
					OPERATORS.includes(filter[1])
			);
		return valid ? filters : null;
	} catch {
		return null;
	}
}

// Where an Overview number's list is in the app, with its filters; null when it is only in the Desk.
const LISTS = {
	"Compliance Item": { name: "Register", view: "all" },
	"Compliance Task": { name: "Filings", view: "open" },
	"Legal Date": { name: "Legal", view: "dates" },
	"Legal Case": { name: "Legal", view: "cases" },
	Trademark: { name: "Legal", view: "marks" },
	"Licence Check Log": { name: "LicenceBlocks", view: "blocked" },
	"Privacy Request": { name: "PrivacyRequests", view: "open" },
	"Personal Data Breach": { name: "Breaches", view: "open" },
};

export function listRoute(card, section) {
	const list = LISTS[card.doctype];
	if (!list || !card.filters?.length) return null;
	return {
		name: list.name,
		query: {
			view: list.view,
			f: JSON.stringify(card.filters),
			label: section ? `${section}: ${card.label}` : card.label,
		},
	};
}
