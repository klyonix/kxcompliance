import { describe, expect, it } from "vitest";
import { recordRoute } from "./records";

describe("where a notification's record opens", () => {
	it("opens records with a page of their own there, and lists for the rest", () => {
		expect(recordRoute("Compliance Item", "CI-26-00006")).toEqual({
			name: "ComplianceItem",
			params: { name: "CI-26-00006" },
		});
		expect(recordRoute("Legal Date", "LD-1")).toEqual({ name: "Legal" });
		expect(recordRoute("Sales Invoice", "SINV-1")).toBeNull();
	});
});
