import { describe, expect, it } from "vitest";
import { onTimeParts, onTimeSummary, valueClass } from "./overview";

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
});
