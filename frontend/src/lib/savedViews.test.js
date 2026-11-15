import { describe, expect, it } from "vitest";
import { readLast, sortViews, viewRecord, viewState, writeLast } from "./savedViews";

const memory = () => {
	const store = new Map();
	return {
		getItem: (key) => store.get(key) ?? null,
		setItem: (key, value) => store.set(key, value),
	};
};

describe("saved views", () => {
	it("list pinned first, then shared, then one's own", () => {
		const views = [
			{ label: "B mine", owner: "me", is_shared: 0, is_pinned: 0 },
			{ label: "A shared", owner: "boss", is_shared: 1, is_pinned: 0 },
			{ label: "Z pinned", owner: "boss", is_shared: 1, is_pinned: 1 },
		];
		expect(sortViews(views, "me").map((view) => view.label)).toEqual([
			"Z pinned",
			"A shared",
			"B mine",
		]);
	});

	it("keep the layout, board, tab and the controls' state, and give them back as they were", () => {
		const snapshot = {
			filters: [{ fieldname: "item_type", operator: "equals", value: "FSSAI Licence" }],
			sort: [{ fieldname: "valid_until", direction: "asc" }],
			columns: [{ fieldname: "title", label: "Title" }],
			quickFilterFields: [],
		};
		const record = viewRecord({
			label: "FSSAI board",
			listKey: "register",
			layout: "kanban",
			board: "register-status",
			baseView: "all",
			snapshot,
			shared: true,
			pinned: false,
		});
		expect(record).toMatchObject({
			layout: "Kanban",
			board: "register-status",
			is_shared: 1,
			is_pinned: 0,
		});
		expect(viewState(record)).toEqual({
			layout: "kanban",
			board: "register-status",
			baseView: "all",
			snapshot,
		});
	});

	it("remember a list's last state on the device, and shrug off a damaged one", () => {
		const storage = memory();
		writeLast("register", { layout: "table", board: "", snapshot: { filters: [] } }, storage);
		expect(readLast("register", storage)).toEqual({
			layout: "table",
			board: "",
			snapshot: { filters: [] },
		});
		storage.setItem("kxcompliance:list2:filings", "{oops");
		expect(readLast("filings", storage)).toBeNull();
	});
});
