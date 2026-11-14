import { describe, expect, it } from "vitest";
import { companiesOf, companyFilters, keepClientWork } from "./clientFilter";

const clients = [
	{ name: "Sunrise Group", companies: ["Sunrise Foods", "Sunrise Mills"] },
	{ name: "New Client", companies: [] },
];

describe("the client filter", () => {
	it("narrows a list to the chosen client's companies", () => {
		const companies = companiesOf(clients, "Sunrise Group");
		expect(companyFilters(companies)).toEqual([
			["company", "in", ["Sunrise Foods", "Sunrise Mills"]],
		]);
		expect(companyFilters(companies, "applicant")[0][0]).toBe("applicant");
	});

	it("leaves a list alone when no client is chosen, or the choice is no longer offered", () => {
		expect(companyFilters(companiesOf(clients, ""))).toEqual([]);
		expect(companyFilters(companiesOf(clients, "Gone Client"))).toEqual([]);
	});

	it("shows nothing for a client with no companies yet", () => {
		const [[, , values]] = companyFilters(companiesOf(clients, "New Client"));
		expect(values).toHaveLength(1);
		expect(values[0]).not.toBe("");
	});

	it("keeps My Work to the client's companies", () => {
		const data = {
			items: [{ company: "Sunrise Foods" }, { company: "Other" }],
			tasks: [{ company: "Sunrise Mills" }],
			legal_dates: [{ company: "Other" }],
			as_of: "now",
		};
		const kept = keepClientWork(data, ["Sunrise Foods", "Sunrise Mills"]);
		expect([kept.items.length, kept.tasks.length, kept.legal_dates.length]).toEqual([1, 1, 0]);
		expect(keepClientWork(data, null)).toBe(data);
	});
});
