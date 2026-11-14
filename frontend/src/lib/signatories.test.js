import { describe, expect, it } from "vitest";
import { signatoryRow } from "./signatories";

describe("signatoryRow", () => {
	it("shows the person's role, company and DIN", () => {
		const row = signatoryRow({
			name: "SIG-00001",
			full_name: "Ravi Rao",
			designation: "Managing Director",
			company: "Sunrise Foods",
			din: "01234567",
			is_active: 1,
		});
		expect(row.detail).toBe("Managing Director · Sunrise Foods · DIN 01234567");
		expect([row.status, row.theme]).toEqual(["Active", "green"]);
	});

	it("marks someone who has left as former", () => {
		expect(signatoryRow({ name: "S", full_name: "A", is_active: 0 }).status).toBe("Former");
	});
});
