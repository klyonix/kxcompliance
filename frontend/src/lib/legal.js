// Rules for showing legal cases, trademarks and their dates, kept apart from the screens so they
// can be tested. They mirror the checks the server makes on save.
import { getList } from "@/api";
import { relativeDue } from "@/pages/myWork";

export const OPEN_CASE_STATUSES = ["Open", "Stayed", "Reserved for Order"];
export const CLOSED_CASE_STATUSES = [
	"Disposed - In Our Favour",
	"Disposed - Against Us",
	"Settled",
	"Withdrawn",
];

// The statuses a case can move to from where it is: closing it, or moving it while open.
export function nextCaseStatuses(current) {
	return [...OPEN_CASE_STATUSES, ...CLOSED_CASE_STATUSES].filter((status) => status !== current);
}

// What closing a case does to the dates still ahead of it.
export function cancelLine(count) {
	if (!count) return "";
	return count === 1
		? "Its 1 scheduled date will be cancelled, so no reminder goes out for it:"
		: `Its ${count} scheduled dates will be cancelled, so no reminders go out for them:`;
}
export const ENDED_MARK_STATUSES = ["Refused", "Abandoned", "Withdrawn", "Removed"];
export const MARK_STATUSES = [
	"New Application",
	"Formalities Check Pass",
	"Marked for Exam",
	"Objected",
	"Accepted and Advertised",
	"Opposed",
	"Registered",
	...ENDED_MARK_STATUSES,
];
// What the registry sends at each stage, asked for as the mark moves there, and the deadline it
// starts. The server holds the same list (legal.MARK_STATUS_FIELDS).
export const MARK_STATUS_FIELDS = {
	Objected: {
		fields: [
			{ name: "examination_report_on", label: "Examination report received on", date: true },
		],
		follows: "The reply is due 30 days after the report; it is added to the dates.",
	},
	"Accepted and Advertised": {
		fields: [
			{ name: "journal_number", label: "Journal number" },
			{ name: "journal_date", label: "Journal date", date: true },
		],
		follows:
			"Anyone may oppose for 4 months from the journal date; the window is added to the dates.",
	},
	Opposed: {
		fields: [
			{ name: "opposition_number", label: "Opposition number" },
			{ name: "opposition_notice_on", label: "Opposition notice received on", date: true },
		],
		follows:
			"The counter-statement is due 2 months after the notice; it is added to the dates.",
	},
	Registered: {
		fields: [
			{ name: "registration_number", label: "Registration number", required: true },
			{ name: "registration_date", label: "Registration date", date: true, required: true },
		],
		follows: "A renewal is added to the register, due ten years from filing.",
	},
};

// The details for a stage that were filled in, and the required ones still missing.
export function markStatusDetails(status, values) {
	const fields = MARK_STATUS_FIELDS[status]?.fields || [];
	const details = {};
	for (const field of fields) {
		const value = String(values[field.name] || "").trim();
		if (value) details[field.name] = value;
	}
	const missing = fields.filter((field) => field.required && !details[field.name]);
	return { details, missing: missing.map((field) => field.label) };
}

// The hearings and deadlines still ahead of a case or trademark, soonest first.
export async function scheduledDates(doctype, name) {
	return (
		await getList("Legal Date", {
			fields: ["name", "kind", "date"],
			filters: [
				["reference_doctype", "=", doctype],
				["reference_name", "=", name],
				["status", "=", "Scheduled"],
			],
			orderBy: "date asc",
			limit: 50,
		})
	).rows;
}
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
	"company",
	"responsible",
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
	"company",
	"responsible",
];
export const MARK_LIST_FIELDS = [
	"name",
	"mark",
	"application_number",
	"status",
	"next_date",
	"applicant",
	"responsible",
];

const RESPONSIBLE = { label: "Responsible", field: "responsible", person: true };

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
		date: legalDate.date,
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
		date: legalCase.next_date,
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
		date: mark.next_date,
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
		group: true,
		columns: [{ label: "Company", field: "company" }, RESPONSIBLE],
		dateLabel: "Date",
		filterBy: { mine: "responsible" },
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
		group: true,
		columns: [{ label: "Forum", field: "forum_name" }, RESPONSIBLE],
		boards: ["cases-status"],
		dateLabel: "Next date",
		filterBy: { mine: "responsible" },
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
		group: true,
		columns: [{ label: "Applicant", field: "applicant" }, RESPONSIBLE],
		dateLabel: "Next date",
		filterBy: { mine: "responsible" },
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
