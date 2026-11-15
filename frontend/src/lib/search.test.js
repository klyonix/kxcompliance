import { describe, expect, it } from "vitest";
import { countText, resultSections, searchTabs } from "./search";

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

describe("the wider search", () => {
	it("lists people, customers and clients, each opening its page", () => {
		const sections = resultSections({
			people: [{ user: "asha@x.com", full_name: "Asha Rao", enabled: 1, last_login: null }],
			customers: [{ name: "CUST-7", party_name: "City Pharmacy", party_group: "" }],
			clients: [{ name: "Mehta Traders", client_name: "Mehta Traders", status: "Active" }],
		});
		expect(sections.map((section) => section.key)).toEqual(["clients", "customers", "people"]);
		expect(sections[1].rows[0].to).toEqual({
			name: "LicenceCheck",
			query: { party_type: "Customer", party: "CUST-7" },
		});
		expect(sections[2].rows[0].to).toEqual({ name: "Person", params: { user: "asha@x.com" } });
	});

	it("tabs each kind with its count, and 30+ where the server stopped", () => {
		const many = Array.from({ length: 30 }, (_, index) => ({
			name: `CI-${index}`,
			title: "x",
		}));
		const tabs = searchTabs(resultSections({ items: many, clients: [{ name: "A" }] }));
		expect(tabs.map((tab) => tab.label)).toEqual(["All 31", "Register 30+", "Clients 1"]);
		expect(countText([])).toBe("0");
	});
});
