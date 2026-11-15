import { describe, expect, it } from "vitest";
import { DSC_TYPE, canAct, itemRow, itemTheme, searchFilter } from "./items";

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
		const cancelled = {
			name: "CI-2",
			title: "Old",
			status: "Cancelled",
			valid_until: "2027-01-01",
		};
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

describe("itemRow for a digital signature", () => {
	it("names the holder and where the token is", () => {
		const row = itemRow({
			name: "CI-9",
			title: "DSC - Ravi Rao",
			item_type: DSC_TYPE,
			status: "Active",
			valid_until: "2027-01-09",
			holder_name: "Ravi Rao",
			custody: "With the Firm",
		});
		expect(row.detail).toBe("Ravi Rao · Token with the firm");
	});

	it("falls back to the company when nobody has recorded the token", () => {
		const row = itemRow({
			name: "CI-9",
			title: "DSC - Ravi Rao",
			item_type: DSC_TYPE,
			status: "Active",
			holder_name: "Ravi Rao",
			company: "Sunrise Foods",
			custody: "",
		});
		expect(row.detail).toBe("Ravi Rao · Sunrise Foods");
	});
});

describe("status and the missing certificate", () => {
	it("shows a planned renewal in blue and the missing certificate first", () => {
		expect(itemTheme("Renewal Planned")).toBe("blue");
		const row = itemRow(
			{
				name: "CI-1",
				title: "Drug Licence, Demo City Pharmacy",
				item_type: "Drug Licence",
				reference_number: "KA-B1-20B-118",
				status: "Renewal Planned",
				valid_until: "2026-12-04",
				certificate_missing: 1,
			},
			new Date("2026-11-15T10:00:00")
		);
		expect(row.detail).toBe("No certificate · Drug Licence · KA-B1-20B-118");
		expect(row.theme).toBe("blue");
	});
});
