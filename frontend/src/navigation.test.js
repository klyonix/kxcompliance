import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { boot } from "./boot";
import {
	CLIENT_ROUTES,
	firstRunRoute,
	isSettingsPageOpen,
	sectionsFor,
	settingsPagesFor,
} from "./navigation";

// Every page the side bar opens, a group's pages included.
const routes = (options) =>
	sectionsFor(options).flatMap((section) => [
		section.route,
		...(section.pages || []).map((page) => page.route),
	]);

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

	it("shows a firm's manager Client billing before it is set up", () => {
		const saved = { ...boot };
		Object.assign(boot, {
			accountType: "CA/CS Firm",
			roles: ["Compliance Manager"],
			mayBill: false,
			billingSetUp: false,
		});
		try {
			expect(routes({ checks: false, client: false })).toContain("Billing");
			boot.roles = ["Compliance User"];
			expect(routes({ checks: false, client: false })).not.toContain("Billing");
			Object.assign(boot, { roles: ["Compliance Manager"], billingSetUp: true });
			expect(routes({ checks: false, client: false })).not.toContain("Billing");
		} finally {
			Object.assign(boot, saved);
		}
	});

	it("puts Client billing under Clients for a firm that bills", () => {
		const saved = { ...boot };
		Object.assign(boot, {
			accountType: "CA/CS Firm",
			roles: ["Compliance Manager"],
			mayBill: true,
			billingSetUp: true,
		});
		try {
			const shown = sectionsFor({ checks: false, client: false });
			expect(shown.map((section) => section.route)).not.toContain("Billing");
			const clients = shown.find((section) => section.route === "Clients");
			expect(clients.pages.map((page) => [page.label, page.route])).toEqual([
				["Clients", "Clients"],
				["Client billing", "Billing"],
			]);
			expect(isSettingsPageOpen(clients.pages[1], "Bill")).toBe(true);
			expect(settingsPagesFor({ firm: true }).map((page) => page.label)).toContain(
				"Billing setup"
			);
			// Before billing is set up the row still opens Client billing, which leads to the setup.
			Object.assign(boot, { mayBill: false, billingSetUp: false });
			const early = sectionsFor({ checks: false, client: false }).find(
				(section) => section.route === "Clients"
			).pages[1];
			expect(early.route).toBe("Billing");
			expect(isSettingsPageOpen(early, "BillingSettings")).toBe(false);
			// Someone who may not bill sees Clients as a plain row.
			Object.assign(boot, { roles: ["Compliance User"], mayBill: false });
			const plain = sectionsFor({ checks: false, client: false });
			expect(plain.find((section) => section.route === "Clients").pages).toBeUndefined();
		} finally {
			Object.assign(boot, saved);
		}
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
