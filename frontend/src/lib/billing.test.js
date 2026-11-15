import { describe, expect, it } from "vitest";
import {
	advanceProblem,
	billState,
	billSubtotal,
	creditProblem,
	linesProblem,
	linesToSend,
	paymentProblem,
	ratesProblem,
	ratesToSend,
	servicesProblem,
} from "./billing";

describe("rates", () => {
	const ret = (template, amount = 100) => ({
		kind: "Return",
		obligation_template: template,
		unit: "Per filing",
		amount,
	});
	const svc = (service, unit = "Per hour", amount = 100) => ({
		kind: "Service",
		service,
		unit,
		amount,
	});

	it("each price a return per filing or a named service, once, at zero or more", () => {
		expect(ratesProblem([])).toBeNull();
		expect(ratesProblem([ret("")])).toMatch(/Choose a return/);
		expect(ratesProblem([svc(" ")])).toMatch(/Name each service/);
		expect(ratesProblem([ret("GSTR-1"), ret("GSTR-1", 200)])).toBe("GSTR-1 has two rates.");
		expect(ratesProblem([{ ...ret("GSTR-1"), unit: "Per month" }])).toMatch(
			/how GSTR-1 is charged/
		);
		expect(ratesProblem([svc("Advisory", "Per filing")])).toMatch(/how Advisory is charged/);
		expect(ratesProblem([ret("GSTR-1", "")])).toMatch(/zero or more/);
		expect(
			ratesProblem([ret("GSTR-1", "0"), svc("Advisory"), svc("Retainer", "Per month")])
		).toBeNull();
	});

	it("are sent with only what each kind needs", () => {
		expect(
			ratesToSend([{ ...svc(" Advisory "), obligation_template: "x", sac_code: " 998231 " }])
		).toEqual([
			{
				kind: "Service",
				obligation_template: null,
				service: "Advisory",
				unit: "Per hour",
				amount: 100,
				sac_code: "998231",
			},
		]);
	});
});

describe("a bill being made", () => {
	it("adds up what is ticked, recurring charges if chosen, services done and typed lines", () => {
		const filings = [
			{ name: "CT-1", fee: 1500 },
			{ name: "CT-2", fee: 800 },
		];
		expect(
			billSubtotal({
				filings,
				ticked: ["CT-1"],
				recurring: [{ amount: 5000 }],
				withRecurring: true,
				services: [{ service: "Advisory", qty: "2.5" }],
				rates: [{ service: "Advisory", amount: 2000 }],
				lines: [{ description: "Advisory", amount: "1000" }],
			})
		).toBe(12500);
		expect(billSubtotal({ filings, ticked: [] })).toBe(0);
		expect(servicesProblem([{ service: "", qty: 1 }])).toMatch(/Choose a service/);
		expect(servicesProblem([{ service: "Advisory", qty: 0 }])).toMatch(/how many hours/);
		expect(servicesProblem([{ service: "Advisory", qty: "1.5" }])).toBeNull();
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

describe("a payment being recorded", () => {
	const due = 11800;
	it("is above zero, with TDS no more than what is left, dated and paid somehow", () => {
		const good = { amount: 5000, tds: 1000, paid_on: "2026-11-10", mode: "UPI" };
		expect(paymentProblem(good, due)).toBeNull();
		expect(paymentProblem({ ...good, amount: 0 }, due)).toMatch(/above zero/);
		expect(paymentProblem({ ...good, tds: -1 }, due)).toMatch(/zero or more/);
		expect(paymentProblem({ ...good, amount: 11000 }, due)).toMatch(/more than the 11800/);
		expect(paymentProblem({ ...good, paid_on: "" }, due)).toMatch(/date/);
		expect(paymentProblem({ ...good, mode: "" }, due)).toMatch(/how it was paid/);
	});
});

describe("a credit note being made", () => {
	it("needs a reason, and on one line an amount up to what is left on it", () => {
		const line = { name: "row1", creditable: 1500 };
		expect(creditProblem({ line: null, reason: "Billed twice" })).toBeNull();
		expect(creditProblem({ line: null, reason: " " })).toMatch(/Say why/);
		expect(creditProblem({ line, amount: 500, reason: "Discount" })).toBeNull();
		expect(creditProblem({ line, amount: 0, reason: "Discount" })).toMatch(/above zero/);
		expect(creditProblem({ line, amount: 1600, reason: "Discount" })).toMatch(
			/at most its 1500/
		);
	});

	it("shows a credit note as one, not as paid", () => {
		expect(billState({ docstatus: 1, is_return: 1, outstanding_amount: 0 }).label).toBe(
			"Credit note"
		);
	});
});

describe("an advance being recorded", () => {
	it("is from a client, above zero, dated and paid somehow", () => {
		const good = { client: "Sunrise", amount: 2000, paid_on: "2026-11-01", mode: "UPI" };
		expect(advanceProblem(good)).toBeNull();
		expect(advanceProblem({ ...good, client: "" })).toMatch(/client/);
		expect(advanceProblem({ ...good, amount: -5 })).toMatch(/above zero/);
		expect(advanceProblem({ ...good, paid_on: "" })).toMatch(/date/);
		expect(advanceProblem({ ...good, mode: "" })).toMatch(/how it was paid/);
	});
});
