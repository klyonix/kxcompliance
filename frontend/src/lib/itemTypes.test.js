import { describe, expect, it } from "vitest";
import { daysText, parseDays, typeRow, typeSummary, typesShown } from "./itemTypes";

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

	it("lists a tab's types by the name typed, as the firm uses them", () => {
		const types = [
			{ name: "Trade Licence", category: "Licence", is_active: 1, renewal_cycle_months: 12 },
			{ name: "Fire NOC", category: "Licence", is_active: 0, set_by_firm: true },
		];
		expect(typesShown(types, "active").map((type) => type.name)).toEqual(["Trade Licence"]);
		expect(typesShown(types, "off").map((type) => type.name)).toEqual(["Fire NOC"]);
		expect(typesShown(types, "all", "fire").map((type) => type.name)).toEqual(["Fire NOC"]);
		expect(typeRow(types[1]).detail).toMatch(/^Your own settings/);
		expect(typeRow(types[0]).cells).toEqual(["Licence", "Every 12 months"]);
	});
});
