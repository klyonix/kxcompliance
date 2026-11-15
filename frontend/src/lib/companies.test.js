import { describe, expect, it } from "vitest";
import { companyGroups } from "./companies";

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
