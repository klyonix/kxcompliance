// The app's search: what each kind of result is called and how it shows, reusing the rows the
// app's own lists already use.
import { taskRow } from "@/lib/filings";
import { itemRow } from "@/lib/items";
import { caseRow, markRow } from "@/lib/legal";
import { partyRow } from "@/lib/licenceCheck";
import { obligationRow } from "@/lib/obligations";
import { personRow } from "@/lib/people";
import { requestRow } from "@/lib/requests";
import { signatoryRow } from "@/lib/signatories";

export const MIN_LENGTH = 2;
// The server looks at this many of each kind; past it, the count reads "30+".
export const CANDIDATES = 30;
// How many of each kind "All" shows before "Show all".
export const PREVIEW = 5;

const none = { text: "", late: false };

const clientRow = (client) => ({
	key: client.name,
	kind: "client",
	title: client.client_name || client.name,
	detail: client.client_kind || "",
	status: client.status || "",
	theme: client.status === "Active" ? "green" : "gray",
	due: none,
	to: { name: "Client", params: { name: client.name } },
});

const companyRow = (profile) => ({
	key: profile.name,
	kind: "company",
	title: profile.company,
	detail: [profile.company_type, profile.client].filter(Boolean).join(" · "),
	status: "",
	due: none,
	to: { name: "Company", params: { company: profile.company } },
});

const ruleRow = (rule) => ({
	key: rule.name,
	kind: "licence-rule",
	title: rule.item_type,
	detail: `${rule.party_type === "Supplier" ? "Suppliers" : "Customers"} need it`,
	status: rule.is_active ? rule.action : "Off",
	theme: !rule.is_active ? "gray" : rule.action === "Block" ? "red" : "amber",
	due: none,
	to: { name: "LicenceRule", params: { name: rule.name } },
});

export const SECTIONS = [
	{ key: "items", label: "Register", toRow: itemRow },
	{ key: "filings", label: "Filings", toRow: taskRow },
	{ key: "cases", label: "Cases", toRow: caseRow },
	{ key: "trademarks", label: "Trademarks", toRow: markRow },
	{ key: "clients", label: "Clients", toRow: clientRow },
	{ key: "companies", label: "Companies", toRow: companyRow },
	{ key: "signatories", label: "Signatories", toRow: signatoryRow },
	{
		key: "requests",
		label: "Document requests",
		toRow: (request, today) => requestRow(request, { today }),
	},
	{ key: "customers", label: "Customers", toRow: (party) => partyRow(party, "Customer") },
	{ key: "suppliers", label: "Suppliers", toRow: (party) => partyRow(party, "Supplier") },
	{ key: "people", label: "People", toRow: personRow },
	{ key: "rules", label: "Licence rules", toRow: ruleRow },
	{ key: "obligations", label: "Obligations", toRow: obligationRow },
];

// A found customer or supplier opens their Licence Check, which partyRow gives as a query only.
const fullRoute = (row) =>
	row.to && !row.to.name && row.to.query
		? { name: "LicenceCheck", query: row.to.query }
		: row.to;

// The sections that found something, each with its rows, in the order above.
export function resultSections(results, today = new Date()) {
	return SECTIONS.map((section) => ({
		...section,
		rows: (results?.[section.key] || []).map((record) => {
			const row = section.toRow(record, today);
			return { ...row, to: fullRoute(row) };
		}),
	})).filter((section) => section.rows.length);
}

// A section's count as the tabs show it: the server's count when known, else what came back,
// "30+" when the server stopped looking.
export const countText = (rows, total) => {
	if (Number.isInteger(total)) return `${total}`;
	return rows.length >= CANDIDATES ? `${CANDIDATES}+` : `${rows.length}`;
};

// The tabs over the results: All, then each kind that found something, with its count. `totals`
// are the server's counts by kind (search_counts), when it has answered.
export function searchTabs(sections, totals = {}) {
	const counted = sections.every((section) => Number.isInteger(totals[section.key]));
	const total = sections.reduce(
		(sum, section) => sum + (counted ? totals[section.key] : section.rows.length),
		0
	);
	return [
		{ label: `All ${total}`, value: "all" },
		...sections.map((section) => ({
			label: `${section.label} ${countText(section.rows, totals[section.key])}`,
			value: section.key,
		})),
	];
}
