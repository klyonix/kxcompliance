import { describe, expect, it } from "vitest";
import { choiceFilters, groupRows } from "./listViews";

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

describe("only mine", () => {
	it("narrows to the person in the list's field, and to nothing without one", () => {
		expect(
			choiceFilters({ mine: true }, { mineField: "responsible", user: "neha@example.com" })
		).toEqual([["responsible", "=", "neha@example.com"]]);
		expect(
			choiceFilters({ mine: false }, { mineField: "responsible", user: "neha@example.com" })
		).toEqual([]);
		expect(choiceFilters({ mine: true }, { user: "neha@example.com" })).toEqual([]);
	});
});
