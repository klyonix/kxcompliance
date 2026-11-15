import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
	CLIENT_ROUTES,
	firstRunRoute,
	isSettingsPageOpen,
	sectionsFor,
	settingsPagesFor,
} from "./navigation";

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

describe("a site's first sign-in", () => {
	// Follow redirects as the router does; a loop never settles.
	function settle(name, flags) {
		let to = { name, fullPath: `/${name}` };
		for (let step = 0; step < 10; step++) {
			const next = firstRunRoute(to, flags);
			if (!next) return to.name;
			to = { ...next, fullPath: `/${next.name}` };
		}
		throw new Error(`no settling from ${name}`);
	}

	it("shows the privacy notice first, even on a new site, without looping", () => {
		const both = { privacyNoticeDue: true, setupNeeded: true };
		expect(settle("MyWork", both)).toBe("PrivacyNotice");
		expect(settle("Onboarding", both)).toBe("PrivacyNotice");
		expect(firstRunRoute({ name: "Billing", fullPath: "/billing" }, both).query.next).toBe(
			"/billing"
		);
	});

	it("then the setup wizard, and never the wizard once set up", () => {
		expect(settle("MyWork", { privacyNoticeDue: false, setupNeeded: true })).toBe(
			"Onboarding"
		);
		expect(settle("PrivacyNotice", { privacyNoticeDue: false, setupNeeded: true })).toBe(
			"Onboarding"
		);
		expect(settle("Onboarding", { privacyNoticeDue: false, setupNeeded: false })).toBe(
			"MyWork"
		);
		expect(settle("Filings", { privacyNoticeDue: false, setupNeeded: false })).toBe("Filings");
	});
});
