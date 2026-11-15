import { describe, expect, it } from "vitest";
import { commentHtml, recordRoute } from "./records";

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

describe("a comment", () => {
	it("is kept as escaped text, line by line", () => {
		expect(commentHtml(" Filed today.\n<script>alert(1)</script> ")).toBe(
			"<p>Filed today.</p><p>&lt;script&gt;alert(1)&lt;/script&gt;</p>"
		);
		expect(commentHtml("a\n\nb")).toBe("<p>a</p><p><br></p><p>b</p>");
	});
});
