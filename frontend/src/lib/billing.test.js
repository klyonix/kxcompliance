import { describe, expect, it } from "vitest";
import {
	accountFacts,
	advanceProblem,
	ageingRows,
	barWidth,
	billState,
	billSubtotal,
	commitmentLines,
	creditProblem,
	linesProblem,
	linesToSend,
	paymentFacts,
	paymentProblem,
	rateLine,
	ratesProblem,
	ratesToSend,
	servicesProblem,
	statementLink,
	statementProblem,
	summaryFacts,
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

describe("a client's year with the firm", () => {
	const summary = {
		commitment: {
			total: 63000,
			recurring: [
				{
					service: "Fixed fee",
					unit: "Per month",
					periods: 12,
					rate: 5000,
					amount: 60000,
				},
			],
			filings: [{ return: "GSTR-3B (Monthly)", count: 1, rate: 3000, amount: 3000 }],
		},
		activity: { billed: 11800, received: 5000, tds: 1000, credited: 0, written_off: 0 },
		outstanding: { outstanding: 5800, not_due: 800, late_30: 5000, late_60: 0 },
		advance: 0,
		unbilled_total: 1500,
	};

	it("says what was expected, billed and received, what is overdue and what is left out", () => {
		const facts = accountFacts(summary);
		expect(facts.map((fact) => fact.label)).toEqual([
			"Expected this year",
			"Billed",
			"Received",
			"Still due",
			"TDS deducted",
			"Not billed yet",
		]);
		const due = facts.find((fact) => fact.label === "Still due");
		expect(due.tone).toBe("red");
		expect(due.detail).toMatch(/overdue/);
	});

	it("breaks the commitment into its charges and filings", () => {
		const lines = commitmentLines(summary.commitment);
		expect(lines.map((line) => line.label)).toEqual(["Fixed fee", "GSTR-3B (Monthly)"]);
		expect(lines[0].detail).toMatch(/^12 months at/);
		expect(lines[1].detail).toMatch(/^1 filing at/);
	});

	it("ages what is due, leaving out empty columns", () => {
		expect(ageingRows(summary.outstanding).map((row) => row.key)).toEqual([
			"not_due",
			"late_30",
		]);
	});

	it("says how each rate is charged", () => {
		expect(
			rateLine({ kind: "Service", service: "Advisory", unit: "Per hour", amount: 2000 })
				.amount
		).toMatch(/an hour$/);
	});

	it("checks a statement's dates and builds its download address", () => {
		expect(statementProblem({ from: "2026-04-01", to: "2027-03-31" })).toBeNull();
		expect(statementProblem({ from: "", to: "2027-03-31" })).toMatch(/first and last/);
		expect(statementProblem({ from: "2027-04-01", to: "2027-03-31" })).toMatch(/after/);
		expect(statementLink("A & B", "2026-04-01", "2027-03-31")).toBe(
			"/api/method/kxcompliance.api.statement_pdf?client=A+%26+B&from_date=2026-04-01&to_date=2027-03-31"
		);
	});
});

describe("a payment's page", () => {
	it("gives the amount, how it came, and TDS and the reference only when there are any", () => {
		const cash = paymentFacts({ paid_amount: 2000, mode_of_payment: "Cash", tds: 0 });
		expect(cash.map((fact) => fact.label)).toEqual(["Received", "How"]);
		const bank = paymentFacts({
			paid_amount: 5000,
			mode_of_payment: "Bank Transfer",
			tds: 1000,
			reference_no: "UTR1",
		});
		expect(bank.map((fact) => fact.label)).toEqual([
			"Received",
			"How",
			"TDS deducted",
			"Reference",
		]);
	});
});

describe("Billing's summary", () => {
	it("says what came in and what is overdue", () => {
		const facts = summaryFacts({
			activity: { billed: 11800, received: 5000, tds: 1000, credited: 0, written_off: 0 },
			ageing: { outstanding: 5800, not_due: 800 },
		});
		expect(facts.map((fact) => fact.label)).toEqual([
			"Billed",
			"Received",
			"Still due",
			"TDS deducted",
			"Credit notes",
			"Written off",
		]);
		expect(facts[2]).toMatchObject({ tone: "red" });
		expect(facts[2].detail).toMatch(/overdue/);
	});

	it("draws each month against the largest", () => {
		const months = [{ total: 2000 }, { total: 500 }];
		expect(barWidth(2000, months)).toBe(100);
		expect(barWidth(500, months)).toBe(25);
		expect(barWidth(-100, months)).toBe(0);
		expect(barWidth(10, [])).toBe(0);
	});
});
