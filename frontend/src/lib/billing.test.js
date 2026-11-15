import { describe, expect, it } from "vitest";
import {
	billState,
	billSubtotal,
	linesProblem,
	linesToSend,
	pricesProblem,
	pricesToSend,
} from "./billing";

describe("prices per return", () => {
	it("need a return each, once, and a fee of zero or more", () => {
		expect(pricesProblem([])).toBeNull();
		expect(pricesProblem([{ obligation_template: "", amount: 100 }])).toMatch(
			/Choose a return/
		);
		expect(
			pricesProblem([
				{ obligation_template: "GSTR-1", amount: 100 },
				{ obligation_template: "GSTR-1", amount: 200 },
			])
		).toBe("GSTR-1 has two prices.");
		expect(pricesProblem([{ obligation_template: "GSTR-1", amount: "" }])).toMatch(
			/fee of zero/
		);
		expect(pricesProblem([{ obligation_template: "GSTR-1", amount: -5 }])).toMatch(
			/fee of zero/
		);
		expect(pricesProblem([{ obligation_template: "GSTR-1", amount: "0" }])).toBeNull();
	});

	it("are sent as a return and a number", () => {
		expect(
			pricesToSend([{ obligation_template: "GSTR-1", amount: "1500", name: "x" }])
		).toEqual([{ obligation_template: "GSTR-1", amount: 1500 }]);
	});
});

describe("a bill being made", () => {
	it("adds up what is ticked, the fixed fee if chosen, and typed lines", () => {
		const filings = [
			{ name: "CT-1", fee: 1500 },
			{ name: "CT-2", fee: 800 },
		];
		expect(
			billSubtotal({
				filings,
				ticked: ["CT-1"],
				fixedFee: 5000,
				withFee: true,
				lines: [{ description: "Advisory", amount: "1000" }],
			})
		).toBe(7500);
		expect(billSubtotal({ filings, ticked: [] })).toBe(0);
	});

	it("needs each typed line to say what it is and an amount", () => {
		expect(linesProblem([{ description: "", amount: 10 }])).toMatch(/what each line/);
		expect(linesProblem([{ description: "Fee", amount: 0 }])).toMatch(/above zero/);
		expect(linesProblem([{ description: "Fee", amount: "250" }])).toBeNull();
		expect(linesToSend([{ description: " ROC fee ", amount: "500", government: 1 }])).toEqual([
			{ description: "ROC fee", amount: 500, government: true },
		]);
	});

	it("says where a bill stands", () => {
		expect(billState({ docstatus: 0 }).label).toBe("Draft");
		expect(billState({ docstatus: 2 }).label).toBe("Cancelled");
		expect(billState({ docstatus: 1, outstanding_amount: 0, grand_total: 100 }).label).toBe(
			"Paid"
		);
		expect(billState({ docstatus: 1, outstanding_amount: 40, grand_total: 100 }).label).toBe(
			"Part paid"
		);
		expect(
			billState({
				docstatus: 1,
				outstanding_amount: 100,
				grand_total: 100,
				status: "Overdue",
			}).label
		).toBe("Overdue");
	});
});
