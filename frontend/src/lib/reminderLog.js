// The reminder log: every reminder, escalation and summary the app sent, to whom and when, so a
// manager can answer "nobody told us".
import { formatDate, formatDateTime } from "@/lib/format";

export const LOG_FIELDS = [
	"name",
	"kind",
	"compliance_item",
	"compliance_task",
	"legal_date",
	"document_request",
	"due_date",
	"sent_to",
	"sent_on",
];

const kindView = (label, value, kind) => ({
	label,
	value,
	filters: kind ? [["kind", "=", kind]] : [],
	orderBy: "sent_on desc",
});
// Four tabs fit beside the search; reminders to customers and suppliers and the weekly summaries
// are under All.
export const LOG_VIEWS = [
	kindView("All", "all"),
	kindView("Reminders", "reminders", "Reminder"),
	kindView("Escalations", "escalations", "Escalation"),
	kindView("Document requests", "requests", "Document Request"),
];

// What a reminder was about, and where that opens in the app.
function about(log) {
	if (log.compliance_task)
		return {
			what: log.compliance_task,
			to: { name: "ComplianceTask", params: { name: log.compliance_task } },
		};
	if (log.compliance_item)
		return {
			what: log.compliance_item,
			to: { name: "ComplianceItem", params: { name: log.compliance_item } },
		};
	if (log.document_request)
		return {
			what: log.document_request,
			to: { name: "DocumentRequest", params: { name: log.document_request } },
		};
	if (log.legal_date) return { what: log.legal_date, to: { name: "Legal" } };
	return { what: "Weekly summary", to: { name: "ReminderLog" } };
}

export function logRow(log) {
	const { what, to } = about(log);
	const recipients = String(log.sent_to || "")
		.split(/[\n,]+/)
		.map((email) => email.trim())
		.filter(Boolean);
	return {
		key: log.name,
		kind: "reminder",
		title: `${log.kind}: ${what}`,
		detail: [
			recipients.length > 2
				? `${recipients.slice(0, 2).join(", ")} and ${recipients.length - 2} more`
				: recipients.join(", "),
			log.due_date && `due ${formatDate(log.due_date)}`,
		]
			.filter(Boolean)
			.join(" · "),
		status: log.kind,
		theme: log.kind === "Escalation" ? "amber" : "gray",
		due: { text: formatDateTime(log.sent_on), late: false },
		to,
	};
}
