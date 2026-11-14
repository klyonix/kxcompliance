import { describe, expect, it } from "vitest";
import { daysText, parseDays, typeSummary } from "./itemTypes";

describe("item types", () => {
	it("reads reminder days as people type them", () => {
		expect(parseDays("30, 60 7;7 x -1")).toEqual([60, 30, 7]);
		expect(parseDays("")).toEqual([]);
	});

	it("writes them back largest first", () => {
		expect(daysText([{ days_before: 7 }, { days_before: 60 }])).toBe("60, 7");
	});

	it("sums a type up in a line", () => {
		expect(
			typeSummary({ category: "Licence", renewal_cycle_months: 12, requires_document: 1 })
		).toBe("Licence · renews every 12 months · certificate needed");
		expect(typeSummary({ category: "Registration", renewal_cycle_months: 0 })).toBe(
			"Registration · does not expire"
		);
	});
});
