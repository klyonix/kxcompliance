// The obligation library and due-date extensions: how their rules read, and how they are listed.
import { formatDate } from "@/lib/format";

export function ordinal(day) {
	const tens = day % 100;
	if (tens >= 11 && tens <= 13) return `${day}th`;
	return `${day}${{ 1: "st", 2: "nd", 3: "rd" }[day % 10] || "th"}`;
}

// "the 20th of the next month", "the last day, 7 months after the period ends"
export function dueText(monthsAfter, dueDay) {
	const months = Number(monthsAfter) || 0;
	const day = Number(dueDay) >= 31 ? "the last day" : `the ${ordinal(Number(dueDay) || 1)}`;
	if (months === 0) return `${day} of the period's last month`;
	if (months === 1) return `${day} of the next month`;
	return `${day}, ${months} months after the period ends`;
}

export function ruleSummary(template) {
	if (template.due_after_event) {
		const days = Number(template.days_after_event) || 0;
		return `${days} days after ${template.event_type || "the AGM"}`;
	}
	return `${frequencyText(template)} · due ${dueText(
		template.months_after_period,
		template.due_day
	)}`;
}

const MONTHS = [
	"Jan",
	"Feb",
	"Mar",
	"Apr",
	"May",
	"Jun",
	"Jul",
	"Aug",
	"Sep",
	"Oct",
	"Nov",
	"Dec",
];

// "Monthly", or "Monthly except Mar, Jun, Sep, Dec" for one that skips months (PMT-06).
function frequencyText(template) {
	const skipped = String(template.skip_months || "")
		.split(",")
		.map((part) => MONTHS[Number(part.trim()) - 1])
		.filter(Boolean);
	return skipped.length
		? `${template.frequency} except ${skipped.join(", ")}`
		: template.frequency;
}

export const OBLIGATION_FIELDS = [
	"name",
	"law",
	"form",
	"frequency",
	"months_after_period",
	"due_day",
	"skip_months",
	"due_after_event",
	"days_after_event",
	"event_type",
	"is_active",
	"is_standard",
];

// `laws` is the order the library lists them in (GST first); each tab groups its rows by law.
export function obligationViews(laws = []) {
	const view = (label, value, filters) => ({
		label,
		value,
		filters,
		orderBy: "name asc",
		group: (template) => template.law,
		groupOrder: laws,
	});
	return [
		view("In use", "active", [["is_active", "=", 1]]),
		view("Off", "off", [["is_active", "=", 0]]),
		view("All", "all", []),
	];
}

// The library's columns (RecordList); an obligation has no date of its own.
export const OBLIGATION_LIST = {
	columns: [
		{ label: "Law", field: "law" },
		{ label: "Form", field: "form" },
	],
	dateLabel: null,
};

export function obligationRow(template) {
	let status = "Standard";
	let theme = "green";
	if (!template.is_active) [status, theme] = ["Off", "gray"];
	else if (!template.is_standard) [status, theme] = ["Your own", "blue"];
	return {
		key: template.name,
		kind: "obligation",
		title: template.name,
		detail: ruleSummary(template),
		status,
		theme,
		due: { text: "", late: false },
		to: { name: "Obligation", params: { name: template.name } },
	};
}

// "One state per line" text ⇄ a list.
export const stateList = (text) =>
	String(text || "")
		.split("\n")
		.map((line) => line.trim())
		.filter(Boolean);

export const isoDate = (date) =>
	[
		date.getFullYear(),
		String(date.getMonth() + 1).padStart(2, "0"),
		String(date.getDate()).padStart(2, "0"),
	].join("-");

export function periodsText(from, to) {
	return from === to
		? `Period ending ${formatDate(from)}`
		: `Periods ending ${formatDate(from)} to ${formatDate(to)}`;
}

export const EXTENSION_FIELDS = [
	"name",
	"obligation_template",
	"periods_ending_from",
	"periods_ending_to",
	"new_due_date",
	"notification_reference",
];

// Extensions still ahead (their new date not yet passed), then the past ones.
export function extensionViews(today = new Date()) {
	const day = isoDate(today);
	return [
		{
			label: "Current",
			value: "current",
			filters: [["new_due_date", ">=", day]],
			orderBy: "new_due_date asc",
		},
		{
			label: "Past",
			value: "past",
			filters: [["new_due_date", "<", day]],
			orderBy: "new_due_date desc",
		},
	];
}

export function extensionRow(extension) {
	return {
		key: extension.name,
		kind: "extension",
		title: extension.obligation_template,
		detail: [
			periodsText(extension.periods_ending_from, extension.periods_ending_to),
			extension.notification_reference,
		]
			.filter(Boolean)
			.join(" · "),
		status: "Extended",
		theme: "blue",
		due: { text: formatDate(extension.new_due_date), late: false },
		to: { name: "Extension", params: { name: extension.name } },
	};
}

// "Moves 12 open filings for 5 companies"
export function previewText({ filings, companies }) {
	if (!filings)
		return "No open filings fall in these periods yet; later ones will take the new date.";
	const things = filings === 1 ? "1 open filing" : `${filings} open filings`;
	const whose = companies === 1 ? "1 company" : `${companies} companies`;
	return `Moves ${things} for ${whose} to the new date.`;
}
