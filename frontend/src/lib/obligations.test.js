import { describe, expect, it } from "vitest";
import {
	dueText,
	extensionViews,
	groupByLaw,
	matchesSearch,
	ordinal,
	previewText,
	ruleSummary,
	stateList,
} from "./obligations";

describe("obligation rules in words", () => {
	it("writes ordinals", () => {
		expect([1, 2, 3, 4, 11, 12, 13, 20, 21, 22, 23].map(ordinal)).toEqual([
			"1st",
			"2nd",
			"3rd",
			"4th",
			"11th",
			"12th",
			"13th",
			"20th",
			"21st",
			"22nd",
			"23rd",
		]);
	});

	it("says when a period's filing is due", () => {
		expect(dueText(1, 20)).toBe("the 20th of the next month");
		expect(dueText(0, 31)).toBe("the last day of the period's last month");
		expect(dueText(7, 31)).toBe("the last day, 7 months after the period ends");
	});

	it("sums up a template", () => {
		expect(ruleSummary({ frequency: "Monthly", months_after_period: 1, due_day: 20 })).toBe(
			"Monthly · due the 20th of the next month"
		);
		expect(ruleSummary({ due_after_event: 1, days_after_event: 30 })).toBe(
			"30 days after the AGM"
		);
		expect(
			ruleSummary({
				due_after_event: 1,
				days_after_event: 30,
				event_type: "Director Change",
			})
		).toBe("30 days after Director Change");
	});
});

describe("listing the library", () => {
	const templates = [
		{ name: "TDS Return 26Q", law: "TDS/TCS", form: "26Q" },
		{ name: "GSTR-3B (Monthly)", law: "GST", form: "GSTR-3B" },
		{ name: "GSTR-1 (Monthly)", law: "GST", form: "GSTR-1" },
		{ name: "Local Body Return", law: "Municipal" },
	];

	it("groups by law in the order the laws are offered, names in order", () => {
		const groups = groupByLaw(templates, ["GST", "Income Tax", "TDS/TCS"]);
		expect(groups.map((group) => group.law)).toEqual(["GST", "TDS/TCS", "Municipal"]);
		expect(groups[0].templates.map((row) => row.name)).toEqual([
			"GSTR-1 (Monthly)",
			"GSTR-3B (Monthly)",
		]);
	});

	it("finds by name, form or law, every word", () => {
		expect(
			templates.filter((row) => matchesSearch(row, "gst 3b")).map((row) => row.name)
		).toEqual(["GSTR-3B (Monthly)"]);
		expect(templates.filter((row) => matchesSearch(row, "tds")).length).toBe(1);
		expect(templates.filter((row) => matchesSearch(row, "")).length).toBe(4);
	});

	it("reads states one per line", () => {
		expect(stateList(" Karnataka\n\nKerala \n")).toEqual(["Karnataka", "Kerala"]);
	});
});

describe("extensions", () => {
	it("splits current and past by today's date", () => {
		const [current, past] = extensionViews(new Date(2026, 10, 5));
		expect(current.filters).toEqual([["new_due_date", ">=", "2026-11-05"]]);
		expect(past.filters).toEqual([["new_due_date", "<", "2026-11-05"]]);
	});

	it("says what saving would move", () => {
		expect(previewText({ filings: 12, companies: 5 })).toBe(
			"Moves 12 open filings for 5 companies to the new date."
		);
		expect(previewText({ filings: 1, companies: 1 })).toBe(
			"Moves 1 open filing for 1 company to the new date."
		);
		expect(previewText({ filings: 0, companies: 0 })).toMatch(/^No open filings/);
	});
});
