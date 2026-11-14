// Rules for showing legal cases, trademarks and their dates, kept apart from the screens so they
// can be tested. They mirror the checks the server makes on save.
import { relativeDue } from "@/pages/myWork";

export const OPEN_CASE_STATUSES = ["Open", "Stayed", "Reserved for Order"];
export const ENDED_MARK_STATUSES = ["Refused", "Abandoned", "Withdrawn", "Removed"];
export const OUTCOME_STATUSES = ["Done", "Adjourned", "Missed"];
export const CASE_TYPES = [
	"Litigation",
	"Tax Notice or Assessment",
	"Labour",
	"Consumer",
	"Arbitration",
	"Regulatory",
	"Other",
];
export const FORUMS = [
	"Supreme Court",
	"High Court",
	"District Court",
	"NCLT/NCLAT",
	"ITAT",
	"GST Appellate Tribunal",
	"Commissioner (Appeals)",
	"Tax Officer",
	"Consumer Commission",
	"Labour Court",
	"Arbitral Tribunal",
	"Other",
];

const PAGES = { "Legal Case": "LegalCase", Trademark: "Trademark" };

// Where a case's or a trademark's page is in the app.
export const referenceRoute = (doctype, name) => ({ name: PAGES[doctype], params: { name } });

const midnightOf = (today) => new Date(today.getFullYear(), today.getMonth(), today.getDate());

export function caseTheme(status) {
	if (status === "Disposed - Against Us") return "red";
	if (["Disposed - In Our Favour", "Settled"].includes(status)) return "green";
	if (status === "Reserved for Order") return "amber";
	if (status === "Open") return "blue";
	return "gray";
}

export function markTheme(status) {
	if (status === "Registered") return "green";
	if (["Objected", "Opposed"].includes(status)) return "amber";
	if (status === "Refused") return "red";
	if (status === "Accepted and Advertised") return "blue";
	return "gray";
}

export function dateTheme(legalDate) {
	if (legalDate.status === "Scheduled") return legalDate.is_overdue ? "red" : "blue";
	if (legalDate.status === "Done") return "green";
	if (legalDate.status === "Adjourned") return "amber";
	if (legalDate.status === "Missed") return "red";
	return "gray";
}

// A Scheduled date that has passed has no outcome yet; say so rather than "Scheduled".
export const dateStatus = (legalDate) =>
	legalDate.status === "Scheduled" && legalDate.is_overdue
		? "Outcome not recorded"
		: legalDate.status;

function nextDue(date, today, closed) {
	if (closed) return { text: "", late: false };
	if (!date) return { text: "No date set", late: false };
	return relativeDue(date, midnightOf(today));
}

export const DATE_LIST_FIELDS = [
	"name",
	"reference_doctype",
	"reference_name",
	"reference_title",
	"kind",
	"date",
	"status",
	"is_overdue",
	"purpose",
];
export const CASE_LIST_FIELDS = [
	"name",
	"title",
	"case_type",
	"forum",
	"forum_name",
	"case_number",
	"status",
	"next_date",
];
export const MARK_LIST_FIELDS = ["name", "mark", "application_number", "status", "next_date"];

export function dateRow(legalDate, today = new Date()) {
	return {
		key: legalDate.name,
		kind: "legal",
		title: legalDate.reference_title || legalDate.reference_name,
		detail: [legalDate.kind, legalDate.purpose].filter(Boolean).join(" · "),
		status: dateStatus(legalDate),
		theme: dateTheme(legalDate),
		due: relativeDue(legalDate.date, midnightOf(today), {
			overdue: Boolean(legalDate.is_overdue),
		}),
		to: referenceRoute(legalDate.reference_doctype, legalDate.reference_name),
	};
}

export function caseRow(legalCase, today = new Date()) {
	return {
		key: legalCase.name,
		kind: "legal",
		title: legalCase.title,
		detail: [
			legalCase.case_type,
			legalCase.forum_name || legalCase.forum,
			legalCase.case_number,
		]
			.filter(Boolean)
			.join(" · "),
		status: legalCase.status,
		theme: caseTheme(legalCase.status),
		due: nextDue(legalCase.next_date, today, !OPEN_CASE_STATUSES.includes(legalCase.status)),
		to: referenceRoute("Legal Case", legalCase.name),
	};
}

export function markRow(mark, today = new Date()) {
	return {
		key: mark.name,
		kind: "trademark",
		title: mark.mark,
		detail: mark.application_number
			? `Application ${mark.application_number}`
			: "No application number yet",
		status: mark.status,
		theme: markTheme(mark.status),
		due: nextDue(mark.next_date, today, ENDED_MARK_STATUSES.includes(mark.status)),
		to: referenceRoute("Trademark", mark.name),
	};
}

export const LEGAL_VIEWS = [
	{
		label: "Coming up",
		value: "dates",
		doctype: "Legal Date",
		fields: DATE_LIST_FIELDS,
		filters: [["status", "=", "Scheduled"]],
		orderBy: "date asc",
		toRow: dateRow,
		searchField: "reference_title",
		searchPlaceholder: "Search by case or mark",
	},
	{
		label: "Cases",
		value: "cases",
		doctype: "Legal Case",
		fields: CASE_LIST_FIELDS,
		filters: [["status", "in", OPEN_CASE_STATUSES]],
		orderBy: "next_date asc",
		toRow: caseRow,
		searchField: "title",
		searchPlaceholder: "Search cases",
	},
	{
		label: "Trademarks",
		value: "marks",
		doctype: "Trademark",
		fields: MARK_LIST_FIELDS,
		filters: [["status", "not in", ENDED_MARK_STATUSES]],
		orderBy: "next_date asc",
		toRow: markRow,
		companyField: "applicant",
		searchField: "mark",
		searchPlaceholder: "Search trademarks",
	},
];

// The server needs a written account of a hearing before it is marked Done or Adjourned.
export function proceedingsError(kind, status, proceedings) {
	if (kind === "Hearing" && ["Done", "Adjourned"].includes(status) && !proceedings?.trim()) {
		return "Write what happened at the hearing.";
	}
	return null;
}

export function nextDateError(date, nextDate) {
	if (nextDate && nextDate <= date) return "The next date must be after this one.";
	return null;
}

// Only the outcome fields that were filled in, so nothing else is sent.
export function outcomeValues({ status, attended_by, proceedings, next_date }) {
	const values = { status };
	if (attended_by?.trim()) values.attended_by = attended_by.trim();
	if (proceedings?.trim()) values.proceedings = proceedings.trim();
	if (next_date && status !== "Missed") values.next_date = next_date;
	return values;
}

// Text Editor fields hold HTML; the app shows them as plain text.
export function plainText(html) {
	if (!html) return "";
	const doc = new DOMParser().parseFromString(html, "text/html");
	return (doc.body.textContent || "").trim();
}
