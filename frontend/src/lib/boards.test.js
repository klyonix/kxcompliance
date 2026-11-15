import { describe, expect, it } from "vitest";
import { BOARDS, groupCards, moveAction } from "./boards";

const card = (key, status) => ({ key, record: { name: key, status } });

describe("Kanban boards", () => {
	it("place each card under its value, and the rest under Other", () => {
		const lanes = groupCards(
			[card("a", "Open"), card("b", "In Progress"), card("c", "Not Applicable")],
			BOARDS["filings-stage"].columns,
			"status"
		);
		expect(lanes.map((lane) => [lane.value, lane.cards.map((entry) => entry.key)])).toEqual([
			["Open", ["a"]],
			["In Progress", ["b"]],
			["Ready for Review", []],
			["Filed", []],
			["Filed Late", []],
			["__other__", ["c"]],
		]);
	});

	it("save a plain move, open the filing for one that needs its details, and leave fixed boards be", () => {
		const filings = BOARDS["filings-stage"];
		expect(moveAction(filings, "Open", "In Progress")).toBe("save");
		expect(moveAction(filings, "In Progress", "Filed")).toBe("open");
		expect(moveAction(filings, "Open", "Open")).toBe("none");
		expect(moveAction(filings, "Open", "__other__")).toBe("none");
		expect(moveAction(BOARDS["register-status"], "Active", "Expired")).toBe("none");
	});

	it("have their own scope, with the recently closed ones dated from today", () => {
		const scope = BOARDS["filings-stage"].scope(new Date("2026-11-15T10:00:00"));
		expect(scope.also).toContainEqual(["filed_on", ">=", "2026-10-16"]);
		expect(BOARDS["register-status"].scope().filters).toEqual([["is_cancelled", "=", 0]]);
	});
});
