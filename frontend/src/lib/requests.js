// Document requests: how one reads in a list and on its page, for the firm and for the client.
import { relativeDue } from "@/pages/myWork";

export const OPEN_REQUEST_STATUSES = ["Requested", "Uploaded"];
export const REQUEST_FIELDS = [
	"name",
	"title",
	"status",
	"is_overdue",
	"due_date",
	"company",
	"compliance_task",
	"details",
	"filing_label",
];

// The status as the reader should see it: the client sees what it has to do, the firm what to check.
export function requestState(request, { client = false } = {}) {
	if (request.status === "Requested") {
		if (request.is_overdue) return { label: "Overdue", theme: "red" };
		return {
			label: client ? "To upload" : "Waiting for client",
			theme: client ? "amber" : "gray",
		};
	}
	if (request.status === "Uploaded") {
		return client
			? { label: "With your firm", theme: "blue" }
			: { label: "To check", theme: "amber" };
	}
	if (request.status === "Accepted") return { label: "Accepted", theme: "green" };
	return { label: request.status, theme: "gray" };
}

export function requestRow(request, { client = false, today = new Date() } = {}) {
	const midnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());
	const state = requestState(request, { client });
	const open = request.status === "Requested";
	return {
		key: request.name,
		kind: "request",
		title: request.title,
		detail: [request.filing_label, request.company].filter(Boolean).join(" · "),
		status: state.label,
		theme: state.theme,
		due: open
			? relativeDue(request.due_date, midnight, { overdue: Boolean(request.is_overdue) })
			: { text: "", late: false },
		to: { name: "DocumentRequest", params: { name: request.name } },
	};
}

// A week from today, or the day before the filing is due if that comes first (never before today).
export function suggestedDueDate(filingDue, today = new Date()) {
	const iso = (date) =>
		`${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(
			date.getDate()
		).padStart(2, "0")}`;
	const week = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 7);
	if (!filingDue) return iso(week);
	const dayBefore = new Date(`${filingDue}T00:00:00`);
	dayBefore.setDate(dayBefore.getDate() - 1);
	const tomorrow = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1);
	if (dayBefore < tomorrow) return iso(tomorrow);
	return iso(dayBefore < week ? dayBefore : week);
}
