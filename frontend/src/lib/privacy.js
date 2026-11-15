import { formatDate, formatDateTime } from "@/lib/format";

// Privacy under the DPDP Act: the requests a person may make about their own data, the status of
// each, and a breach's deadline at the Data Protection Board.

export const REQUEST_TYPES = [
	{ value: "See my data", label: "See my data" },
	{ value: "Correct my data", label: "Correct my data" },
	{ value: "Erase my data", label: "Erase my data" },
	{ value: "Grievance", label: "Raise a grievance" },
];

export const REQUEST_STATUS_THEMES = {
	Open: "amber",
	"In Progress": "blue",
	Done: "green",
	Declined: "gray",
};

export const REQUEST_FIELDS = [
	"name",
	"request_type",
	"requester_name",
	"requested_by",
	"details",
	"status",
	"due_by",
	"closed_on",
];

// The oldest first while waiting, as each is due 90 days after it came in.
export const REQUEST_VIEWS = [
	{
		label: "To answer",
		value: "open",
		filters: [["status", "in", ["Open", "In Progress"]]],
		orderBy: "due_by asc",
		dateLabel: "Answer by",
	},
	{
		label: "Answered",
		value: "closed",
		filters: [["status", "in", ["Done", "Declined"]]],
		orderBy: "closed_on desc",
		dateLabel: "Answered",
	},
];

export function requestRow(request, today = new Date()) {
	const open = !request.closed_on;
	const due = request.due_by ? new Date(`${request.due_by}T23:59:59`) : null;
	return {
		key: request.name,
		kind: "privacy-request",
		title: `${request.request_type}: ${request.requester_name || request.requested_by}`,
		detail: request.details,
		status: request.status,
		theme: REQUEST_STATUS_THEMES[request.status] || "gray",
		due:
			open && due
				? { text: formatDate(request.due_by), late: due < today }
				: { text: formatDate(request.closed_on), late: false },
		to: { name: "PrivacyRequest", params: { name: request.name } },
	};
}

export const BREACH_STATUS_THEMES = {
	"Board not told": "red",
	"People not told": "amber",
	Reported: "green",
};

export const BREACH_FIELDS = [
	"name",
	"title",
	"discovered_on",
	"board_due_by",
	"board_reported_on",
	"status",
	"people_affected",
];

export const BREACH_VIEWS = [
	{
		label: "Not reported",
		value: "open",
		filters: [["status", "!=", "Reported"]],
		orderBy: "discovered_on desc",
	},
	{
		label: "Reported",
		value: "reported",
		filters: [["status", "=", "Reported"]],
		orderBy: "discovered_on desc",
	},
];

export function breachRow(breach, now = new Date()) {
	const hours = boardHoursLeft(breach, now);
	return {
		key: breach.name,
		kind: "breach",
		title: breach.title,
		detail: [
			`Found ${formatDateTime(breach.discovered_on)}`,
			breach.people_affected ? `${breach.people_affected} people affected` : "",
		]
			.filter(Boolean)
			.join(" · "),
		status: breach.status,
		theme: BREACH_STATUS_THEMES[breach.status] || "gray",
		due:
			hours === null
				? { text: "", late: false }
				: { text: hours >= 0 ? `${hours}h left` : `${-hours}h late`, late: hours < 0 },
		to: { name: "Breach", params: { name: breach.name } },
	};
}

// Hours left to report a breach to the Board, below zero once late; null once reported.
export function boardHoursLeft(breach, now = new Date()) {
	if (breach.board_reported_on || !breach.board_due_by) return null;
	const due = new Date(breach.board_due_by.replace(" ", "T"));
	return Math.round((due - now) / 3_600_000);
}

// "Report to the Board within 5 hours", "The Board's report is 3 hours late".
export function boardDeadline(breach, now = new Date()) {
	const hours = boardHoursLeft(breach, now);
	if (hours === null) return "";
	const plural = (count) => `${count} hour${count === 1 ? "" : "s"}`;
	if (hours > 0) return `Report to the Board within ${plural(hours)}`;
	if (hours === 0) return "Report to the Board now";
	return `The Board's report is ${plural(-hours)} late`;
}

// A PAN or mobile number the server sent masked ("XXXXXXXX", "987XXXXXX"): only managers see it.
export const isMasked = (value) => /X{6,}/.test(value || "");

// Where to go after accepting the notice: a page of this app, never another site.
export function safeNext(next) {
	return typeof next === "string" && next.startsWith("/") && !next.startsWith("//") ? next : "/";
}
