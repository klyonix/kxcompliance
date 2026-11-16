// The reports, as the app offers them: the same reports the Desk runs (so the numbers always
// agree), each with a line on what it answers, its filters, and who may open it.
//
// `totals` marks a report the Desk adds a total row to.
//
// A filter is a date, a fixed list, or a list read from the site (`source`): companies, clients,
// people, register item types, branches or brands. `default` may be "today", "in30" (a month
// ahead), "yearStart" or "yearEnd" (the Indian financial year, April to March).
import { isoDate } from "@/lib/obligations";

const COMPANY = { fieldname: "company", label: "Company", type: "link", source: "company" };
const RESPONSIBLE = {
	fieldname: "responsible",
	label: "Responsible",
	type: "link",
	source: "user",
};
const select = (fieldname, label, options) => ({ fieldname, label, type: "select", options });

export const LAWS = [
	"GST",
	"Income Tax",
	"TDS/TCS",
	"PF",
	"ESI",
	"Professional Tax",
	"Labour Welfare Fund",
	"Companies Act",
	"LLP Act",
	"Other",
];
const ITEM_STATUSES = [
	"Active",
	"Due for Renewal",
	"Renewal Planned",
	"Renewal in Progress",
	"Expired",
	"Lapsed",
	"Cancelled",
];

export const AREAS = ["Filings", "Register", "Legal", "Clients", "Billing"];

// The icon each area's heading carries on the Reports page, the same as its side bar section.
export const AREA_ICONS = {
	Filings: "lucide-calendar-check",
	Register: "lucide-file-badge",
	Legal: "lucide-scale",
	Clients: "lucide-users",
	Billing: "lucide-receipt",
};

export const REPORTS = [
	{
		slug: "on-time-filing",
		totals: true,
		name: "On-time Filing",
		area: "Filings",
		title: "On-time filing",
		about: "How many filings were filed on time, late or are overdue, and the fees paid, by company, client, law or person.",
		filters: [
			select("group_by", "Group by", ["Company", "Client", "Law", "Responsible"]),
			COMPANY,
			{ fieldname: "client", label: "Client", type: "link", source: "client", firm: true },
			{ fieldname: "from_date", label: "Due from", type: "date" },
			{ fieldname: "to_date", label: "Due to", type: "date" },
		],
		defaults: { group_by: "Company" },
	},
	{
		slug: "compliance-calendar",
		name: "Compliance Calendar",
		area: "Filings",
		title: "Filings in a month",
		about: "Every filing due in a month, with its status, who files it and its acknowledgement.",
		filters: [
			{ fieldname: "month", label: "Any day in the month", type: "date", required: true },
			COMPANY,
			select("law", "Law", LAWS),
			select("status", "Status", [
				"Open",
				"In Progress",
				"Ready for Review",
				"Filed",
				"Filed Late",
				"Not Applicable",
				"Cancelled",
			]),
			RESPONSIBLE,
		],
		defaults: { month: "today" },
	},
	{
		slug: "compliance-register",
		name: "Compliance Register",
		area: "Register",
		title: "Register",
		about: "Every licence, registration, certificate and policy, with its reference and validity.",
		filters: [
			COMPANY,
			{ fieldname: "branch", label: "Branch", type: "link", source: "branch" },
			{ fieldname: "state", label: "State", type: "text" },
			{ fieldname: "item_type", label: "Type", type: "link", source: "itemType" },
			select("status", "Status", ITEM_STATUSES),
			RESPONSIBLE,
		],
	},
	{
		slug: "compliance-cost",
		totals: true,
		name: "Compliance Cost",
		area: "Register",
		title: "What compliance costs",
		about: "The yearly cost of licences, subscriptions and policies, by type and supplier.",
		filters: [
			COMPANY,
			select("category", "Category", [
				"Licence",
				"Registration",
				"Certificate",
				"Insurance",
				"Subscription",
				"Contract",
				"Other",
			]),
		],
	},
	{
		slug: "party-licence-register",
		name: "Party Licence Register",
		area: "Register",
		title: "Customer and supplier licences",
		about: "The licences your customers and suppliers hold, and whether each is valid.",
		licenceCheck: true,
		filters: [
			select("holder_type", "Held by", ["Customer", "Supplier"]),
			{ fieldname: "item_type", label: "Licence", type: "link", source: "itemType" },
			select("status", "Status", ITEM_STATUSES),
		],
	},
	{
		slug: "legal-calendar",
		name: "Legal Calendar",
		area: "Legal",
		title: "Legal dates",
		about: "Hearings, reply dates and trademark deadlines between two dates.",
		filters: [
			{ fieldname: "from_date", label: "From", type: "date", required: true },
			{ fieldname: "to_date", label: "To", type: "date", required: true },
			select("reference_doctype", "For", ["Legal Case", "Trademark"]),
			select("status", "Status", ["Scheduled", "Done", "Adjourned", "Missed", "Cancelled"]),
			RESPONSIBLE,
		],
		defaults: { from_date: "today", to_date: "in30" },
	},
	{
		slug: "case-register",
		name: "Case Register",
		area: "Legal",
		title: "Notices and cases",
		about: "Every notice and case with its forum, status, next date and risk.",
		filters: [
			COMPANY,
			select("case_type", "Type", [
				"Litigation",
				"Tax Notice or Assessment",
				"Labour",
				"Consumer",
				"Arbitration",
				"Regulatory",
				"Other",
			]),
			select("status", "Status", [
				"Open",
				"Stayed",
				"Reserved for Order",
				"Disposed - In Our Favour",
				"Disposed - Against Us",
				"Settled",
				"Withdrawn",
			]),
			select("risk", "Risk", ["Probable", "Possible", "Remote"]),
			RESPONSIBLE,
		],
	},
	{
		slug: "contingent-liabilities",
		totals: true,
		name: "Contingent Liabilities",
		area: "Legal",
		title: "Contingent liabilities",
		about: "Amounts at stake in open cases, what is provided for and what is not, as at a date. For the accounts' notes.",
		managersOrAuditors: true,
		filters: [{ fieldname: "as_at", label: "As at", type: "date", required: true }, COMPANY],
		defaults: { as_at: "today" },
	},
	{
		slug: "trademark-register",
		name: "Trademark Register",
		area: "Legal",
		title: "Trademarks",
		about: "Every trademark application and registration with its status.",
		filters: [
			{ fieldname: "applicant", label: "Applicant", type: "link", source: "company" },
			{ fieldname: "brand", label: "Brand", type: "link", source: "brand" },
			select("status", "Status", [
				"New Application",
				"Formalities Check Pass",
				"Marked for Exam",
				"Objected",
				"Accepted and Advertised",
				"Opposed",
				"Registered",
				"Refused",
				"Abandoned",
				"Withdrawn",
				"Removed",
			]),
		],
	},
	{
		slug: "client-summary",
		totals: true,
		name: "Client Summary",
		area: "Clients",
		title: "Clients at a glance",
		about: "Each client's filings on time and late, fees, open cases, documents awaited, DSCs and lowest score.",
		firm: true,
		filters: [
			{ fieldname: "from_date", label: "Due from", type: "date", required: true },
			{ fieldname: "to_date", label: "Due to", type: "date", required: true },
			{ fieldname: "client", label: "Client", type: "link", source: "client" },
			{
				fieldname: "relationship_manager",
				label: "Relationship manager",
				type: "link",
				source: "user",
			},
		],
		defaults: { from_date: "yearStart", to_date: "yearEnd" },
	},
	// A firm's own bills, for those who may bill (the reports' roles are ERPNext's accounts roles).
	{
		slug: "billing-outstanding",
		totals: true,
		name: "Billing Outstanding",
		area: "Billing",
		title: "What clients owe",
		about: "Each client's bills still due, by how late: not yet due, 1-30, 31-60, 61-90 and over 90 days.",
		billing: true,
		filters: [{ fieldname: "client", label: "Client", type: "link", source: "client" }],
	},
	{
		slug: "billing-by-month",
		totals: true,
		name: "Billing by Month",
		area: "Billing",
		title: "Billing by month",
		about: "Bills sent each month: before GST, GST, total, what has been received and what is still due.",
		billing: true,
		filters: [
			{ fieldname: "from_date", label: "Billed from", type: "date", required: true },
			{ fieldname: "to_date", label: "Billed to", type: "date", required: true },
			{ fieldname: "client", label: "Client", type: "link", source: "client" },
		],
		defaults: { from_date: "yearStart", to_date: "yearEnd" },
	},
	{
		slug: "unbilled-filings",
		totals: true,
		name: "Unbilled Filings",
		area: "Billing",
		title: "Filed, not billed",
		about: "Returns filed for clients, with a price, that are on no bill yet, and their fees.",
		billing: true,
		filters: [{ fieldname: "client", label: "Client", type: "link", source: "client" }],
	},
];

export const reportBySlug = (slug) => REPORTS.find((report) => report.slug === slug);

// The reports this person may open, by the same rules as the Desk's report roles and the side bar.
export function reportsFor({ firm, manager, auditor, licenceCheck = !firm, bills = false }) {
	return REPORTS.filter((report) => {
		if (report.firm && !firm) return false;
		if (report.billing && !bills) return false;
		if (report.organisation && firm) return false;
		if (report.licenceCheck && !licenceCheck) return false;
		if (report.managersOrAuditors && !(manager || auditor)) return false;
		return true;
	});
}

// The reports whose title or line on what it answers holds every word typed, in any order.
export function matchReports(reports, query) {
	const words = query.toLowerCase().split(/\s+/).filter(Boolean);
	if (!words.length) return reports;
	return reports.filter((report) => {
		const text = `${report.title} ${report.about} ${report.area}`.toLowerCase();
		return words.every((word) => text.includes(word));
	});
}

const RECENT_KEY = "kxcompliance:recent-reports";
const RECENT_MAX = 3;

// The reports last opened on this device, newest first, so the ones used daily sit on top.
export function recentReports(reports, storage = localStorage) {
	let slugs = [];
	try {
		slugs = JSON.parse(storage.getItem(RECENT_KEY) || "[]");
	} catch {
		slugs = [];
	}
	if (!Array.isArray(slugs)) return [];
	return slugs
		.map((slug) => reports.find((report) => report.slug === slug))
		.filter(Boolean)
		.slice(0, RECENT_MAX);
}

export function rememberOpened(slug, storage = localStorage) {
	const kept = recentReports(REPORTS, storage).map((report) => report.slug);
	const slugs = [slug, ...kept.filter((other) => other !== slug)].slice(0, RECENT_MAX);
	storage.setItem(RECENT_KEY, JSON.stringify(slugs));
}

// The financial year (April to March) holding `today`.
export function financialYear(today = new Date()) {
	const startYear = today.getMonth() >= 3 ? today.getFullYear() : today.getFullYear() - 1;
	return { start: `${startYear}-04-01`, end: `${startYear + 1}-03-31` };
}

export function defaultValue(code, today = new Date()) {
	if (code === "today") return isoDate(today);
	if (code === "in30") {
		const later = new Date(today);
		later.setDate(later.getDate() + 30);
		return isoDate(later);
	}
	if (code === "yearStart") return financialYear(today).start;
	if (code === "yearEnd") return financialYear(today).end;
	return code;
}

// The filters a report opens with, from the address (so a link can carry them) over its defaults.
export function initialFilters(report, query = {}, today = new Date()) {
	const values = {};
	for (const filter of report.filters) {
		const fromQuery = query[filter.fieldname];
		values[filter.fieldname] =
			typeof fromQuery === "string"
				? fromQuery
				: defaultValue(report.defaults?.[filter.fieldname] ?? "", today);
	}
	return values;
}

// Only filters with a value are sent; empty ones mean "all".
export const filledFilters = (values) =>
	Object.fromEntries(
		Object.entries(values).filter(([, value]) => value !== "" && value != null)
	);

export const missingRequired = (report, values) =>
	report.filters.filter((filter) => filter.required && !values[filter.fieldname]);

// Where a report's link column opens in the app.
const RECORD_ROUTES = {
	"Compliance Task": "ComplianceTask",
	"Compliance Item": "ComplianceItem",
	"Legal Case": "LegalCase",
	Trademark: "Trademark",
	"Compliance Client": "Client",
	"Document Request": "DocumentRequest",
};
export function linkRoute(column, value) {
	if (column.fieldtype !== "Link" || !value) return null;
	const name = RECORD_ROUTES[column.options];
	return name ? { name, params: { name: value } } : null;
}

// The Desk adds a report's total row as its last row; it is shown as the table's foot, not
// counted or sorted with the rest.
export function splitTotal(rows, hasTotal) {
	if (!hasTotal || !rows.length) return { rows, total: null };
	return { rows: rows.slice(0, -1), total: rows[rows.length - 1] };
}

// Rows as objects: a report may answer with lists in column order.
export function rowsOf(result, columns) {
	return (result || [])
		.filter((row) => row && typeof row === "object")
		.map((row) =>
			Array.isArray(row)
				? Object.fromEntries(
						columns.map((column, index) => [column.fieldname, row[index]])
				  )
				: row
		);
}

export function sortRows(rows, fieldname, descending) {
	const sorted = [...rows].sort((a, b) => {
		const x = a[fieldname];
		const y = b[fieldname];
		if (x == null || x === "") return 1;
		if (y == null || y === "") return -1;
		return typeof x === "number" && typeof y === "number"
			? x - y
			: String(x).localeCompare(String(y), undefined, { numeric: true });
	});
	return descending ? sorted.reverse() : sorted;
}

// A CSV of what is on screen, for opening in a spreadsheet.
export function toCsv(columns, rows) {
	const cell = (value) => {
		const text = value == null ? "" : String(value);
		return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
	};
	const lines = [columns.map((column) => cell(column.label)).join(",")];
	for (const row of rows)
		lines.push(columns.map((column) => cell(row[column.fieldname])).join(","));
	return lines.join("\n");
}

// A firm with one client chosen opens a report on that client: its Client filter, or its Company
// filter when the client has just one company. An organisation with one company chosen opens it
// on that company. A filter given in the address wins.
export function clientDefaults(report, query = {}, { client = "", companies = null } = {}) {
	const has = (fieldname) => report.filters.some((filter) => filter.fieldname === fieldname);
	const given = typeof query.client === "string" || typeof query.company === "string";
	if (given) return {};
	if (client && has("client")) return { client };
	if (has("company") && companies?.length === 1) return { company: companies[0] };
	return {};
}
