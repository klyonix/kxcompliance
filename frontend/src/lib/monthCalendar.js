// The month calendar: the grid of days, what falls on each, and where each thing opens.
import { isoDate } from "@/lib/obligations";

// What the calendar can show, each with its colour and an on/off switch.
export const KINDS = [
	{ key: "filing", label: "Filings", dot: "bg-surface-blue-5" },
	{ key: "licence", label: "Expiries", dot: "bg-surface-amber-5" },
	{ key: "legal", label: "Legal dates", dot: "bg-surface-violet-5" },
	{ key: "request", label: "Documents due", dot: "bg-surface-teal-5" },
];
export const kindOf = (key) => KINDS.find((kind) => kind.key === key);

// "2026-11" → { year: 2026, month: 10 } (months counted from 0, as Date does); bad input → this month.
export function parseMonth(text, today = new Date()) {
	const match = /^(\d{4})-(\d{2})$/.exec(String(text || ""));
	if (match && Number(match[2]) >= 1 && Number(match[2]) <= 12) {
		return { year: Number(match[1]), month: Number(match[2]) - 1 };
	}
	return { year: today.getFullYear(), month: today.getMonth() };
}

export const monthKey = ({ year, month }) => `${year}-${String(month + 1).padStart(2, "0")}`;

export function shiftMonth({ year, month }, by) {
	const date = new Date(year, month + by, 1);
	return { year: date.getFullYear(), month: date.getMonth() };
}

export const monthTitle = ({ year, month }) =>
	new Date(year, month, 1).toLocaleDateString("en-GB", { month: "long", year: "numeric" });

// Weeks from Sunday to Saturday covering the month, as calendars in India are laid out.
export function monthGrid({ year, month }, today = new Date()) {
	const first = new Date(year, month, 1);
	const start = new Date(year, month, 1 - first.getDay());
	const last = new Date(year, month + 1, 0);
	const end = new Date(year, month + 1, 0 + (6 - last.getDay()));
	const todayKey = isoDate(today);
	const weeks = [];
	for (let day = new Date(start); day <= end; day.setDate(day.getDate() + 1)) {
		if (day.getDay() === 0) weeks.push([]);
		const date = isoDate(day);
		weeks[weeks.length - 1].push({
			date,
			day: day.getDate(),
			inMonth: day.getMonth() === month,
			isToday: date === todayKey,
		});
	}
	return weeks;
}

export const gridRange = (weeks) => ({
	start: weeks[0][0].date,
	end: weeks[weeks.length - 1][6].date,
});

export function eventsByDay(events, shown) {
	const days = {};
	for (const event of events) {
		if (!shown.includes(event.kind)) continue;
		(days[event.date] ||= []).push(event);
	}
	return days;
}

const LEGAL_PAGES = { "Legal Case": "LegalCase", Trademark: "Trademark" };

export function eventRoute(event) {
	if (event.kind === "filing") return { name: "ComplianceTask", params: { name: event.name } };
	if (event.kind === "licence") return { name: "ComplianceItem", params: { name: event.name } };
	if (event.kind === "request") return { name: "DocumentRequest", params: { name: event.name } };
	const page = LEGAL_PAGES[event.reference_doctype];
	return page ? { name: page, params: { name: event.reference_name } } : { name: "Legal" };
}

// The same event as a row of a list, for the day's list under the grid.
export function eventRow(event) {
	return {
		key: `${event.kind}-${event.name}`,
		kind: event.kind,
		title: event.title,
		detail: event.detail || "",
		status: event.status,
		theme: event.overdue ? "red" : event.done ? "green" : "gray",
		due: { text: event.time || "", late: event.overdue },
		to: eventRoute(event),
	};
}
