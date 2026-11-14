import { describe, expect, it } from "vitest";
import { importSummary, sortedRows, summaryLine } from "./bulkSetup";

const rows = [
	{ row_number: 2, outcome: "Ready" },
	{ row_number: 3, outcome: "Skipped" },
	{ row_number: 4, outcome: "Error" },
	{ row_number: 5, outcome: "Ready" },
];

describe("bulk setup", () => {
	it("says what a checked sheet will do", () => {
		expect(summaryLine(importSummary(rows), "Checked")).toBe(
			"2 companies ready to set up · 1 already set up · 1 row to fix"
		);
	});

	it("says how an import went", () => {
		const done = rows.map((row) =>
			row.outcome === "Ready" ? { ...row, outcome: "Made" } : row
		);
		expect(summaryLine(importSummary(done), "Done")).toBe(
			"2 companies set up · 1 row not set up"
		);
		expect(summaryLine(importSummary([{ outcome: "Made" }]), "Done")).toBe("1 company set up");
	});

	it("puts rows to fix first, then keeps the sheet's order", () => {
		expect(sortedRows(rows).map((row) => row.row_number)).toEqual([4, 2, 3, 5]);
	});
});
