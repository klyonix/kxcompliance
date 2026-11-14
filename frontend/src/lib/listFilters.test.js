import { describe, expect, it } from "vitest";
import { listRoute, parseListFilters } from "./listFilters";

describe("lists opened from an Overview number", () => {
	it("read back only well-formed filters", () => {
		expect(
			parseListFilters('[["status","in",["Expired","Lapsed"]],["is_overdue","=",1]]')
		).toEqual([
			["status", "in", ["Expired", "Lapsed"]],
			["is_overdue", "=", 1],
		]);
		expect(parseListFilters("not json")).toBeNull();
		expect(parseListFilters('[["status","drop table",1]]')).toBeNull();
		expect(parseListFilters('[["status; --","=",1]]')).toBeNull();
		expect(parseListFilters("[]")).toBeNull();
		expect(parseListFilters(undefined)).toBeNull();
	});

	it("open the app's list for what the number counts", () => {
		const card = {
			label: "Overdue",
			doctype: "Compliance Task",
			filters: [["is_overdue", "=", 1]],
		};
		expect(listRoute(card, "Filings")).toEqual({
			name: "Filings",
			query: { view: "open", f: '[["is_overdue","=",1]]', label: "Filings: Overdue" },
		});
		expect(listRoute({ ...card, doctype: "Licence Check Log" }).name).toBe("LicenceBlocks");
		expect(listRoute({ ...card, doctype: "Company" })).toBeNull();
	});
});
