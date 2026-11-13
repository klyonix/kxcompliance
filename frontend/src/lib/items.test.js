import { describe, expect, it } from "vitest";
import { canAct, itemRow, itemTheme, searchFilter } from "./items";

describe("compliance items in the app", () => {
	it("colours a status by how pressing it is", () => {
		expect(itemTheme("Lapsed")).toBe("red");
		expect(itemTheme("Due for Renewal")).toBe("amber");
		expect(itemTheme("Renewal in Progress")).toBe("blue");
		expect(itemTheme("Active")).toBe("green");
	});

	it("turns an item into a row that opens its page", () => {
		const row = itemRow(
			{
				name: "CI-26-00007",
				title: "Fire NOC, Peenya",
				item_type: "Fire NOC",
				reference_number: "FN/2026/118",
				status: "Expired",
				valid_until: "2026-11-04",
			},
			new Date(2026, 10, 14)
		);
		expect(row).toMatchObject({
			detail: "Fire NOC · FN/2026/118",
			theme: "red",
			due: { text: "10 days late", late: true },
			to: { name: "ComplianceItem", params: { name: "CI-26-00007" } },
		});
		expect(itemRow({ name: "CI-1", title: "PAN", status: "Active" }).due.text).toBe(
			"No expiry"
		);
		const cancelled = { name: "CI-2", title: "Old", status: "Cancelled", valid_until: "2027-01-01" };
		expect(itemRow(cancelled).due.text).toBe("");
	});

	it("lets managers and the item's people act, and nobody on a cancelled item", () => {
		const item = { responsible: "asha@example.com", reviewer: "ravi@example.com" };
		expect(canAct(item, { user: "asha@example.com", roles: ["Compliance User"] })).toBe(true);
		expect(canAct(item, { user: "meera@example.com", roles: ["Compliance User"] })).toBe(
			false
		);
		expect(canAct(item, { user: "meera@example.com", roles: ["Compliance Auditor"] })).toBe(
			false
		);
		expect(canAct(item, { user: "meera@example.com", roles: ["Compliance Manager"] })).toBe(
			true
		);
		expect(
			canAct(
				{ ...item, is_cancelled: 1 },
				{ user: "asha@example.com", roles: ["Compliance Manager"] }
			)
		).toBe(false);
	});

	it("searches titles only when something is typed", () => {
		expect(searchFilter("  ")).toEqual([]);
		expect(searchFilter("fire")).toEqual([["title", "like", "%fire%"]]);
	});
});
