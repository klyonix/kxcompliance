// Where a record opens in the app, by its type; null for a record that has no page here.
const PAGES = {
	"Compliance Item": "ComplianceItem",
	"Compliance Task": "ComplianceTask",
	"Document Request": "DocumentRequest",
	"Legal Case": "LegalCase",
	Trademark: "Trademark",
	"Compliance Client": "Client",
	"Privacy Request": "PrivacyRequest",
	"Personal Data Breach": "Breach",
	Signatory: "Signatory",
};

// Lists for record types whose rows open somewhere else.
const LISTS = { "Legal Date": { name: "Legal" }, "Licence Check Log": { name: "LicenceBlocks" } };

export function recordRoute(doctype, name) {
	if (PAGES[doctype] && name) return { name: PAGES[doctype], params: { name } };
	return LISTS[doctype] || null;
}

// What someone typed in a comment box, as the HTML a Comment holds: escaped, line by line.
export function commentHtml(text) {
	const escape = (line) =>
		line
			.replaceAll("&", "&amp;")
			.replaceAll("<", "&lt;")
			.replaceAll(">", "&gt;")
			.replaceAll('"', "&quot;")
			.replaceAll("'", "&#39;");
	return text
		.trim()
		.split("\n")
		.map((line) => `<p>${escape(line) || "<br>"}</p>`)
		.join("");
}

// A saved record's page has its activity beside it, so it is wider than a new record's form.
// A client's login does not see the activity. Full class names, for Tailwind to find.
export const showsActivity = (name, { client = false } = {}) => Boolean(name) && !client;
export const recordWidth = (name, options) =>
	showsActivity(name, options) ? "max-w-6xl" : "max-w-3xl";
