import { describe, expect, it } from "vitest";
import { companyGroups, filterCompanies } from "./companies";

describe("the companies list", () => {
	it("lists companies set up first, then those still to set up", () => {
		const groups = companyGroups({
			companies: [
				{
					company: "Acme Pvt Ltd",
					company_type: "Private Limited",
					client: "",
					registrations: 3,
					obligations: 17,
				},
			],
			not_set_up: ["Acme Exports LLP"],
		});
		expect(groups.map((group) => group.key)).toEqual(["set-up", "not-set-up"]);
		expect(groups[0].rows[0].cells).toEqual(["3", "17"]);
		expect(groups[1].rows[0].to).toEqual({
			name: "CompanyNew",
			query: { company: "Acme Exports LLP" },
		});
	});

	it("leaves out a group with nothing in it", () => {
		expect(companyGroups({ companies: [], not_set_up: [] })).toEqual([]);
	});
});

describe("filtering the companies", () => {
	const overview = {
		companies: [
			{ company: "Sunrise Foods", client: "Sunrise" },
			{ company: "Moon Retail", client: "Moon" },
		],
		not_set_up: ["Sunrise Exports", "Other Co"],
	};

	it("keeps a client's companies, set up only", () => {
		expect(filterCompanies(overview, { client: "Sunrise" })).toEqual({
			companies: [{ company: "Sunrise Foods", client: "Sunrise" }],
			not_set_up: [],
		});
	});

	it("searches names, and shows set up or not", () => {
		const found = filterCompanies(overview, { text: "sunrise" });
		expect(found.companies.map((row) => row.company)).toEqual(["Sunrise Foods"]);
		expect(found.not_set_up).toEqual(["Sunrise Exports"]);
		expect(filterCompanies(overview, { show: "not-set-up" }).companies).toEqual([]);
		expect(filterCompanies(overview, { show: "set-up" }).not_set_up).toEqual([]);
	});
});
