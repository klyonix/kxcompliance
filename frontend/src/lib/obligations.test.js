import { describe, expect, it } from "vitest";
import {
	dueText,
	extensionViews,
	obligationRow,
	obligationViews,
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
	const template = {
		name: "GSTR-3B (Monthly)",
		law: "GST",
		frequency: "Monthly",
		months_after_period: 1,
		due_day: 20,
		is_active: 1,
		is_standard: 1,
	};

	it("marks standard, own and switched-off obligations", () => {
		expect(obligationRow(template).status).toBe("Standard");
		expect(obligationRow({ ...template, is_standard: 0 }).status).toBe("Your own");
		expect(obligationRow({ ...template, is_standard: 0, is_active: 0 }).status).toBe("Off");
	});

	it("groups every tab by law, in the order the laws are offered", () => {
		const views = obligationViews(["GST", "Income Tax"]);
		expect(views.map((view) => view.value)).toEqual(["active", "off", "all"]);
		expect(views[0].group(template)).toBe("GST");
		expect(views[2].groupOrder).toEqual(["GST", "Income Tax"]);
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
