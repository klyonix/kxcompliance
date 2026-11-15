import { t } from "@/lib/i18n";
// Turn the my_work answer into rows: what each thing is, when it is due, and how pressing it is.

export const KINDS = {
	licence: { label: "Licences", icon: "lucide-file-badge" },
	filing: { label: "Filings", icon: "lucide-calendar-check" },
	legal: { label: "Legal", icon: "lucide-scale" },
	trademark: { label: "Trademarks", icon: "lucide-stamp" },
	request: { label: "Document requests", icon: "lucide-file-up" },
	signatory: { label: "Signatories", icon: "lucide-pen-line" },
	extension: { label: "Due-date extensions", icon: "lucide-calendar-clock" },
	reminder: { label: "Reminders", icon: "lucide-bell" },
	"privacy-request": { label: "Privacy requests", icon: "lucide-user-lock" },
	breach: { label: "Data breaches", icon: "lucide-shield-alert" },
};

const LEGAL_PAGES = { "Legal Case": "LegalCase", Trademark: "Trademark" };

export const BUCKETS = [
	{ key: "overdue", label: "Overdue" },
	{ key: "week", label: "This week" },
	{ key: "later", label: "Later" },
];

const OVERDUE_ITEM_STATUSES = ["Expired", "Lapsed"];
const DAY = 24 * 60 * 60 * 1000;

const toDate = (value) => (value ? new Date(`${value}T00:00:00`) : null);
export const daysBetween = (from, to) => Math.round((to - from) / DAY);

export function relativeDue(date, today, { overdue = false } = {}) {
	if (!date) return { text: t("No date"), late: overdue };
	const days = daysBetween(today, toDate(date));
	if (days < 0)
		return { text: days === -1 ? t("1 day late") : t("{0} days late", -days), late: true };
	if (overdue) return { text: t("Needs attention"), late: true };
	if (days === 0) return { text: t("Today"), late: false };
	if (days === 1) return { text: t("Tomorrow"), late: false };
	return { text: t("In {0} days", days), late: false };
}

export function bucketFor(row, today) {
	if (row.overdue) return "overdue";
	const date = toDate(row.date);
	if (date && daysBetween(today, date) <= 7) return "week";
	return "later";
}

function themeFor(status, overdue) {
	if (overdue) return "red";
	if (["Due for Renewal", "Ready for Review"].includes(status)) return "amber";
	if (["Renewal in Progress", "In Progress"].includes(status)) return "blue";
	return "gray";
}

export function workRows(work, { today = new Date() } = {}) {
	const midnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());
	const rows = [
		...work.items.map((item) => ({
			key: `item-${item.name}`,
			kind: "licence",
			title: item.title,
			detail: item.item_type,
			status: item.status,
			date: item.valid_until,
			overdue: OVERDUE_ITEM_STATUSES.includes(item.status),
			to: { name: "ComplianceItem", params: { name: item.name } },
		})),
		...work.tasks.map((task) => ({
			key: `task-${task.name}`,
			kind: "filing",
			title: task.obligation_template,
			detail: `${task.period_label} · ${task.company}`,
			status: task.status,
			date: task.effective_due_date,
			overdue: Boolean(task.is_overdue),
			to: { name: "ComplianceTask", params: { name: task.name } },
		})),
		...work.legal_dates.map((legalDate) => ({
			key: `legal-${legalDate.name}`,
			kind: "legal",
			title: legalDate.reference_title || legalDate.reference_name,
			detail: legalDate.kind,
			status: legalDate.is_overdue ? "Outcome not recorded" : "Scheduled",
			date: legalDate.date,
			overdue: Boolean(legalDate.is_overdue),
			to: {
				name: LEGAL_PAGES[legalDate.reference_doctype],
				params: { name: legalDate.reference_name },
			},
		})),
	];
	for (const row of rows) {
		row.theme = themeFor(row.status, row.overdue);
		row.due = relativeDue(row.date, midnight, { overdue: row.overdue });
		row.bucket = bucketFor(row, midnight);
	}
	return rows.sort((a, b) => (a.date || "9999").localeCompare(b.date || "9999"));
}

export function summarise(rows) {
	const counts = Object.fromEntries(BUCKETS.map((bucket) => [bucket.key, 0]));
	for (const row of rows) counts[row.bucket] += 1;
	return counts;
}
