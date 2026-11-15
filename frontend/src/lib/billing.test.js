import { describe, expect, it } from "vitest";
import { pricesProblem, pricesToSend } from "./billing";

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
