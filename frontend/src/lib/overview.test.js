import { describe, expect, it } from "vitest";
import {
	areaKind,
	isQuiet,
	needingCount,
	needsYou,
	onTimeParts,
	onTimeSummary,
	showPercent,
	valueClass,
} from "./overview";

describe("the overview", () => {
	it("colours a number only when there is something to look at", () => {
		expect(valueClass({ value: 3, tone: "red" })).toBe("text-ink-red-5");
		expect(valueClass({ value: 0, tone: "red" })).toBe("text-ink-gray-4");
	});

	it("splits the on-time bar by share and leaves out empty parts", () => {
		const parts = onTimeParts({ on_time: 6, late: 2, overdue: 0, percent: 75 });
		expect(parts.map((part) => [part.key, part.share])).toEqual([
			["on_time", 75],
			["late", 25],
		]);
		expect(onTimeParts({ on_time: 0, late: 0, overdue: 0, percent: null })).toEqual([]);
	});

	it("says so when nothing fell due", () => {
		expect(onTimeSummary({ percent: null })).toMatch(/^No filings/);
		expect(onTimeSummary({ percent: 75 })).toMatch(/^of filings/);
	});

	it("shows no percentage before anything is filed", () => {
		const nothingFiled = { on_time: 0, late: 0, overdue: 1, percent: 0 };
		expect(showPercent(nothingFiled)).toBe(false);
		expect(onTimeSummary(nothingFiled)).toMatch(/^Nothing has been filed yet/);
		expect(showPercent({ on_time: 0, late: 2, overdue: 1, percent: 0 })).toBe(true);
	});

	it("puts what needs someone first, the most urgent first", () => {
		const sections = [
			{
				title: "Register",
				cards: [
					{ label: "Due for renewal", value: 2, tone: "amber", act: true },
					{ label: "Active", value: 9, tone: "green", act: false },
				],
			},
			{
				title: "Filings",
				cards: [
					{ label: "Waiting for review", value: 1, tone: "blue", act: true },
					{ label: "Overdue", value: 3, tone: "red", act: true },
					{ label: "Due this week", value: 0, tone: "amber", act: true },
				],
			},
		];
		expect(needsYou(sections).map((card) => [card.section, card.label])).toEqual([
			["Filings", "Overdue"],
			["Register", "Due for renewal"],
			["Filings", "Waiting for review"],
		]);
		expect(isQuiet(sections[0])).toBe(false);
		expect(isQuiet({ cards: [{ value: 0 }, { value: 0 }] })).toBe(true);
	});
});

describe("the Overview's areas", () => {
	it("colour each area as its rows are coloured", () => {
		expect(areaKind({ key: "filings" })).toBe("filing");
		expect(areaKind({ key: "something-new" })).toBe("");
	});

	it("count the numbers that need someone", () => {
		const section = {
			cards: [
				{ value: 2, tone: "red" },
				{ value: 0, tone: "red" },
				{ value: 3, tone: "blue" },
				{ value: 1, tone: "amber" },
			],
		};
		expect(needingCount(section)).toBe(2);
	});
});
