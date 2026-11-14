import { describe, expect, it } from "vitest";
import {
	eventRoute,
	eventRow,
	eventsByDay,
	gridRange,
	monthGrid,
	monthKey,
	parseMonth,
	shiftMonth,
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
