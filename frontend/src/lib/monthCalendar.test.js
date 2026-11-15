import { describe, expect, it } from "vitest";
import {
	eventRoute,
	eventRow,
	eventsByDay,
	filterEvents,
	gridRange,
	monthGrid,
	monthKey,
	parseFocus,
	parseMonth,
	rangeFor,
	shiftFocus,
	shiftMonth,
	viewTitle,
	weekDays,
} from "./monthCalendar";

describe("the month grid", () => {
	it("covers the month in whole weeks from Sunday, marking today", () => {
		const weeks = monthGrid({ year: 2026, month: 10 }, new Date(2026, 10, 15));
		// November 2026 starts on a Sunday and ends on a Monday.
		expect(weeks.length).toBe(5);
		expect(weeks.every((week) => week.length === 7)).toBe(true);
		expect(gridRange(weeks)).toEqual({ start: "2026-11-01", end: "2026-12-05" });
		expect(weeks[2][0]).toEqual({ date: "2026-11-15", day: 15, inMonth: true, isToday: true });
		expect(weeks[4][6].inMonth).toBe(false);
	});

	it("starts in the previous month when the 1st is mid-week", () => {
		const weeks = monthGrid({ year: 2026, month: 11 });
		expect(gridRange(weeks).start).toBe("2026-11-29");
	});

	it("reads and moves months, falling back to this month", () => {
		expect(parseMonth("2026-11")).toEqual({ year: 2026, month: 10 });
		expect(parseMonth("nonsense", new Date(2027, 0, 9))).toEqual({ year: 2027, month: 0 });
		expect(monthKey(shiftMonth({ year: 2026, month: 11 }, 1))).toBe("2027-01");
		expect(monthKey(shiftMonth({ year: 2026, month: 0 }, -1))).toBe("2025-12");
	});
});

describe("what falls on each day", () => {
	const events = [
		{ kind: "filing", name: "CT-1", date: "2026-11-20", title: "GSTR-3B" },
		{ kind: "licence", name: "CI-1", date: "2026-11-20", title: "Trade licence" },
		{
			kind: "legal",
			name: "LD-1",
			date: "2026-11-21",
			title: "Hearing",
			reference_doctype: "Legal Case",
			reference_name: "LC-1",
		},
	];

	it("groups by day, showing only the kinds switched on", () => {
		const days = eventsByDay(events, ["filing", "legal"]);
		expect(Object.keys(days)).toEqual(["2026-11-20", "2026-11-21"]);
		expect(days["2026-11-20"].map((event) => event.name)).toEqual(["CT-1"]);
	});

	it("opens each thing where it lives", () => {
		expect(eventRoute(events[0])).toEqual({
			name: "ComplianceTask",
			params: { name: "CT-1" },
		});
		expect(eventRoute(events[2])).toEqual({ name: "LegalCase", params: { name: "LC-1" } });
		expect(eventRoute({ kind: "request", name: "DR-1" }).name).toBe("DocumentRequest");
	});

	it("shows overdue in red and done in green in the day's list", () => {
		expect(eventRow({ ...events[0], overdue: true }).theme).toBe("red");
		expect(eventRow({ ...events[0], done: true }).theme).toBe("green");
		expect(eventRow({ ...events[2], time: "10:30" }).due.text).toBe("10:30");
	});
});

describe("the week and day views", () => {
	it("lay a week out from Sunday, marking today", () => {
		const days = weekDays("2026-11-18", new Date(2026, 10, 18));
		expect(days.map((day) => day.date)).toEqual([
			"2026-11-15",
			"2026-11-16",
			"2026-11-17",
			"2026-11-18",
			"2026-11-19",
			"2026-11-20",
			"2026-11-21",
		]);
		expect(days[3].isToday).toBe(true);
	});

	it("load what each view shows", () => {
		expect(rangeFor("day", "2026-11-18")).toEqual({ start: "2026-11-18", end: "2026-11-18" });
		expect(rangeFor("week", "2026-11-18")).toEqual({ start: "2026-11-15", end: "2026-11-21" });
		expect(rangeFor("month", "2026-11-18")).toEqual({
			start: "2026-11-01",
			end: "2026-12-05",
		});
	});

	it("move by a day, a week or a month, across month ends", () => {
		expect(shiftFocus("day", "2026-11-30", 1)).toBe("2026-12-01");
		expect(shiftFocus("week", "2026-11-28", 1)).toBe("2026-12-05");
		expect(shiftFocus("month", "2026-11-18", -1)).toBe("2026-10-01");
	});

	it("title each view", () => {
		expect(viewTitle("month", "2026-11-18")).toBe("November 2026");
		expect(viewTitle("week", "2026-11-18")).toBe("15 – 21 Nov 2026");
		expect(viewTitle("week", "2026-11-30")).toBe("29 Nov – 5 Dec 2026");
		expect(viewTitle("day", "2026-11-18")).toBe("Wednesday, 18 November 2026");
	});

	it("read a date from the address, or today", () => {
		const today = new Date(2026, 10, 15);
		expect(parseFocus("2026-11-18", today)).toBe("2026-11-18");
		expect(parseFocus("soon", today)).toBe("2026-11-15");
	});
});

describe("the calendar's filters", () => {
	const events = [
		{ kind: "filing", responsible: "asha@x.com", done: false },
		{ kind: "filing", responsible: "ravi@x.com", done: true },
		{ kind: "legal", responsible: "asha@x.com", done: true },
	];
	const shown = ["filing", "legal"];

	it("keep only mine, one person's, or what is still open", () => {
		expect(filterEvents(events, { shown, mine: true, user: "asha@x.com" }).length).toBe(2);
		expect(filterEvents(events, { shown, person: "ravi@x.com" }).length).toBe(1);
		expect(filterEvents(events, { shown, open: true }).length).toBe(1);
		expect(filterEvents(events, { shown: ["legal"] }).length).toBe(1);
	});
});
