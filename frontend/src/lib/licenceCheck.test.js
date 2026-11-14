import { describe, expect, it } from "vitest";
import { coverage, licenceState, requirementState, verdict } from "./licenceCheck";

const drug = {
	item_type: "Drug Licence",
	action: "Block",
	grace_days: 0,
	item_groups: ["Drugs", "Vaccines"],
	documents: ["Sales Order", "Sales Invoice"],
	result: "ok",
	message: "",
};
const fssai = { ...drug, item_type: "FSSAI Licence", action: "Warn", item_groups: [] };
const check = (requirements, party_type = "Customer") => ({
	party_type,
	party_name: "City Pharmacy",
	requirements,
});

describe("the licence check", () => {
	it("blocks when a blocking licence is missing, whatever else is in order", () => {
		const answer = verdict(check([{ ...drug, result: "expired" }, fssai]));
		expect(answer).toMatchObject({
			theme: "red",
			title: "Selling to City Pharmacy is blocked",
		});
		expect(answer.detail).toMatch(/^Sales of/);
		expect(verdict(check([{ ...drug, result: "missing" }], "Supplier")).title).toBe(
			"Buying from City Pharmacy is blocked"
		);
	});

	it("warns when only warning licences are missing, and clears when all are held", () => {
		expect(verdict(check([drug, { ...fssai, result: "missing" }])).theme).toBe("amber");
		expect(verdict(check([drug, fssai])).theme).toBe("green");
		expect(verdict(check([])).title).toBe("No licence is required");
	});

	it("says what a requirement covers", () => {
		expect(coverage(drug)).toBe(
			"Needed for items in Drugs, Vaccines, on Sales Order, Sales Invoice"
		);
		expect(coverage({ ...fssai, documents: [] })).toBe(
			"Needed for every item, on no document yet"
		);
	});

	it("colours a gap by whether it blocks or warns", () => {
		expect(requirementState({ ...drug, result: "missing" })).toEqual({
			label: "Missing",
			theme: "red",
		});
		expect(requirementState({ ...fssai, result: "expired" })).toEqual({
			label: "Expired",
			theme: "amber",
		});
		expect(requirementState(drug)).toEqual({ label: "In order", theme: "green" });
	});

	it("flags a licence that expires within a month", () => {
		const on = "2026-11-14";
		expect(licenceState({ valid: true, valid_until: "2026-12-01" }, on)).toMatchObject({
			label: "Expires soon",
			detail: "Expires in 17 days",
		});
		expect(licenceState({ valid: true, valid_until: "2027-06-30" }, on).label).toBe("Valid");
		expect(licenceState({ valid: true, valid_until: null }, on).detail).toBe("No expiry");
		expect(licenceState({ valid: false, valid_until: "2026-10-31" }, on).label).toBe(
			"Expired"
		);
		expect(licenceState({ valid: false, valid_until: "2027-06-30" }, on).label).toBe(
			"Not yet in force"
		);
	});
});
