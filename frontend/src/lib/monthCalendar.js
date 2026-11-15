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

// The calendar's three views over one focus date: a month grid, a week of days, one day.
export const VIEWS = [
	{ label: "Month", value: "month" },
	{ label: "Week", value: "week" },
	{ label: "Day", value: "day" },
];

const asDate = (iso) => new Date(`${iso}T00:00:00`);
export const shiftDate = (iso, days) => {
	const date = asDate(iso);
	date.setDate(date.getDate() + days);
	return isoDate(date);
};

// A date from the address, or today: "2026-11-18" → itself; anything else → today.
export const parseFocus = (text, today = new Date()) =>
	/^\d{4}-\d{2}-\d{2}$/.test(String(text || "")) && !isNaN(asDate(text)) ? text : isoDate(today);

// The week from Sunday to Saturday holding `focus`, as the month grid lays weeks out.
export function weekDays(focus, today = new Date()) {
	const start = shiftDate(focus, -asDate(focus).getDay());
	const todayKey = isoDate(today);
	return Array.from({ length: 7 }, (_, index) => {
		const date = shiftDate(start, index);
		return { date, day: asDate(date).getDate(), isToday: date === todayKey };
	});
}

// What a view shows around its focus date, for loading.
export function rangeFor(view, focus) {
	if (view === "day") return { start: focus, end: focus };
	if (view === "week") {
		const days = weekDays(focus);
		return { start: days[0].date, end: days[6].date };
	}
	const { year, month } = parseMonth(focus.slice(0, 7));
	return gridRange(monthGrid({ year, month }));
}

// Back or on by one month, week or day. A month move lands on the 1st of that month.
export function shiftFocus(view, focus, by) {
	if (view === "day") return shiftDate(focus, by);
	if (view === "week") return shiftDate(focus, by * 7);
	const { year, month } = shiftMonth(parseMonth(focus.slice(0, 7)), by);
	return `${monthKey({ year, month })}-01`;
}

export function viewTitle(view, focus) {
	if (view === "month") return monthTitle(parseMonth(focus.slice(0, 7)));
	if (view === "day") {
		return asDate(focus).toLocaleDateString("en-GB", {
			weekday: "long",
			day: "numeric",
			month: "long",
			year: "numeric",
		});
	}
	const days = weekDays(focus);
	const first = asDate(days[0].date);
	const last = asDate(days[6].date);
	const sameMonth = first.getMonth() === last.getMonth();
	const start = first.toLocaleDateString(
		"en-GB",
		sameMonth ? { day: "numeric" } : { day: "numeric", month: "short" }
	);
	const end = last.toLocaleDateString("en-GB", {
		day: "numeric",
		month: "short",
		year: "numeric",
	});
	return `${start} – ${end}`;
}

// The events the filters keep: the kinds shown, only `user`'s ("Only mine") or one person's,
// and only what is still to do ("Open only").
export function filterEvents(
	events,
	{ shown, mine = false, open = false, person = "", user = "" }
) {
	return events.filter(
		(event) =>
			shown.includes(event.kind) &&
			(!mine || event.responsible === user) &&
			(!person || event.responsible === person) &&
			(!open || !event.done)
	);
}
