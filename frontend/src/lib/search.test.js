import { describe, expect, it } from "vitest";
import { resultSections } from "./search";

describe("search results", () => {
	it("keeps only the sections that found something, each as rows that open their page", () => {
		const sections = resultSections(
			{
				items: [
					{
						name: "CI-1",
						title: "Fire NOC, Peenya",
						status: "Active",
						valid_until: "2027-03-31",
					},
				],
				filings: [],
				cases: [
					{ name: "CASE-1", title: "GST show cause", status: "Open", next_date: null },
				],
				trademarks: [],
			},
			new Date(2026, 10, 14)
		);
		expect(sections.map((section) => section.label)).toEqual(["Register", "Cases"]);
		expect(sections[0].rows[0].to).toEqual({
			name: "ComplianceItem",
			params: { name: "CI-1" },
		});
		expect(sections[1].rows[0].to).toEqual({ name: "LegalCase", params: { name: "CASE-1" } });
	});

	it("shows nothing before a search", () => {
		expect(resultSections(null)).toEqual([]);
	});
});
