import { describe, expect, it } from "vitest";
import {
	goToItems,
	matchItems,
	recentSearches,
	rememberSearch,
	shortcutLabel,
} from "./quickSearch";

const memory = () => {
	const store = {};
	return { getItem: (key) => store[key] ?? null, setItem: (key, value) => (store[key] = value) };
};

describe("quick search", () => {
	it("keeps the last five searches, newest first, each once", () => {
		const storage = memory();
		for (const query of ["gst", "fire noc", "gst", "a", "pune", "tds", "drug", "pf"]) {
			rememberSearch(query, storage);
		}
		expect(recentSearches(storage)).toEqual(["pf", "drug", "tds", "pune", "gst"]);
	});

	it("offers pages and the actions a person may take", () => {
		const menu = [
			{ label: "Search", route: "Search" },
			{ label: "Filings", route: "Filings", icon: "lucide-calendar-check" },
		];
		const staff = goToItems({ menu, settings: [], manager: false, records: true, firm: true });
		expect(staff.map((item) => item.label)).toEqual([
			"Filings",
			"New register item",
			"Log a notice",
			"Start a case",
			"Add a trademark",
			"Record an event",
			"Add a signatory",
		]);
		const auditor = goToItems({ menu, settings: [], manager: false, records: false });
		expect(auditor.map((item) => item.group)).toEqual(["Go to"]);
	});

	it("matches every word of a page or action's name", () => {
		const items = [{ label: "New register item" }, { label: "Register" }];
		expect(matchItems(items, "item new").map((item) => item.label)).toEqual([
			"New register item",
		]);
		expect(matchItems(items, "").length).toBe(2);
	});

	it("names the shortcut for the computer", () => {
		expect(shortcutLabel("MacIntel")).toBe("⌘K");
		expect(shortcutLabel("Win32")).toBe("Ctrl+K");
	});
});
