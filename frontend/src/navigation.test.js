import { describe, expect, it } from "vitest";
import { CLIENT_ROUTES, sectionsFor } from "./navigation";

const routes = (options) => sectionsFor(options).map((section) => section.route);

describe("sectionsFor", () => {
	it("keeps a client's login to its home and its companies' records", () => {
		expect(routes({ checks: false, client: true })).toEqual([
			"Search",
			"ClientHome",
			"Filings",
			"Register",
			"Legal",
		]);
	});

	it("gives a client's login only screens it may open", () => {
		for (const route of routes({ checks: false, client: true })) {
			expect(CLIENT_ROUTES).toContain(route);
		}
		expect(CLIENT_ROUTES).not.toContain("MyWork");
		expect(CLIENT_ROUTES).not.toContain("LicenceCheck");
	});

	it("never shows firm staff the client's home", () => {
		expect(routes({ checks: false, client: false })).not.toContain("ClientHome");
	});

	it("keeps sales and purchase users to the Licence Check", () => {
		expect(routes({ checks: true, client: false })).toEqual(["LicenceCheck"]);
	});
});
