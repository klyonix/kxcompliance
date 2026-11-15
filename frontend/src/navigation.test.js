import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { CLIENT_ROUTES, isSettingsPageOpen, sectionsFor, settingsPagesFor } from "./navigation";

const routes = (options) => sectionsFor(options).map((section) => section.route);

describe("sectionsFor", () => {
	it("keeps a client's login to its home and its companies' records", () => {
		expect(routes({ checks: false, client: true })).toEqual([
			"Search",
			"ClientHome",
			"Filings",
			"Register",
			"Legal",
			"Help",
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

describe("settings pages", () => {
	const routerSource = readFileSync(path.join(import.meta.dirname, "router.js"), "utf8");
	const routeNames = new Set(
		[...routerSource.matchAll(/name: "([A-Za-z]+)"/g)].map((m) => m[1])
	);

	it("open real screens, with the pages opened from them", () => {
		for (const page of settingsPagesFor({ licenceCheck: true })) {
			expect(routeNames).toContain(page.route);
			for (const name of page.also || []) expect(routeNames).toContain(name);
		}
	});

	it("leave licence rules out where licences are not checked", () => {
		const firm = settingsPagesFor({ licenceCheck: false }).map((page) => page.route);
		expect(firm).not.toContain("LicenceRules");
		expect(settingsPagesFor({ licenceCheck: true }).map((page) => page.route)).toContain(
			"LicenceRules"
		);
	});

	it("keep a page's row marked while a record opened from it is open", () => {
		const [rules] = settingsPagesFor({ licenceCheck: true }).filter(
			(page) => page.route === "LicenceRules"
		);
		expect(isSettingsPageOpen(rules, "LicenceRule")).toBe(true);
		expect(isSettingsPageOpen(rules, "LicenceRules")).toBe(true);
		expect(isSettingsPageOpen(rules, "People")).toBe(false);
	});
});
