import { describe, expect, it } from "vitest";
import { choiceCount, choiceFilters, groupRows, orderFor, readListChoices } from "./listViews";

const TODAY = new Date("2026-11-15T10:00:00");
const row = (key, date, late = false) => ({ key, date, due: { text: "", late } });

describe("grouping a list by when", () => {
	it("puts each row under Overdue, Next 30 days, Later or No date, in order", () => {
		const groups = groupRows(
			[
				row("late", "2026-10-05"),
				row("flagged", "2026-11-20", true),
				row("soon", "2026-12-04"),
				row("later", "2027-09-10"),
				row("none", null),
				{ ...row("cancelled", "2026-11-20"), closed: true },
			],
			TODAY
		);
		expect(groups.map((group) => [group.label, group.rows.map((entry) => entry.key)])).toEqual(
			[
				["Overdue", ["late", "flagged"]],
				["Next 30 days", ["soon"]],
				["Later", ["later"]],
				["No date", ["none"]],
				["Closed", ["cancelled"]],
			]
		);
	});

	it("leaves out empty groups", () => {
		expect(groupRows([row("soon", "2026-11-16")], TODAY).map((group) => group.key)).toEqual([
			"soon",
		]);
	});
});

describe("filters and sort from the address", () => {
	const sorts = [
		{ label: "Expiry date", value: "expiry", orderBy: "valid_until asc" },
		{ label: "Name", value: "name", orderBy: "title asc" },
	];

	it("keeps only what the list offers", () => {
		expect(
			readListChoices(
				{ sort: "name", company: "Demo Ltd", type: "FSSAI Licence", mine: "1" },
				{ sorts, companies: ["Demo Ltd"], types: ["FSSAI Licence"] }
			)
		).toEqual({ sort: "name", company: "Demo Ltd", type: "FSSAI Licence", mine: true });
		expect(
			readListChoices(
				{ sort: "creation desc; drop", company: "Someone Else", type: ["x"], mine: "yes" },
				{ sorts, companies: ["Demo Ltd"], types: ["FSSAI Licence"] }
			)
		).toEqual({});
	});

	it("turns the choices into server filters and an order", () => {
		const choices = { company: "Demo Ltd", type: "FSSAI Licence", mine: true, sort: "name" };
		expect(
			choiceFilters(choices, {
				companyField: "applicant",
				typeField: "item_type",
				mineField: "responsible",
				user: "neha@example.com",
			})
		).toEqual([
			["applicant", "=", "Demo Ltd"],
			["item_type", "=", "FSSAI Licence"],
			["responsible", "=", "neha@example.com"],
		]);
		expect(orderFor(choices, sorts, "valid_until asc")).toBe("title asc");
		expect(orderFor({}, sorts, "valid_until asc")).toBe("valid_until asc");
		expect(choiceCount(choices)).toBe(3);
	});
});
