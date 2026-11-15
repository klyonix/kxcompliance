// Tours point at what pages draw. A step naming a marker no page carries would quietly stop
// showing after a screen changed, so the build fails instead. Every page has a tour unless it is
// listed here with the reason it needs none, and the server knows every tour by its id.
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { TOURS } from "./tours";
import { selectorOf, stepsFor, toursForReader } from "./useTours";

const SRC = path.resolve(import.meta.dirname, "..");
const files = (dir) =>
	readdirSync(dir).flatMap((name) => {
		const full = path.join(dir, name);
		if (statSync(full).isDirectory()) return files(full);
		return /\.vue$/.test(name) ? [full] : [];
	});
const source = files(SRC)
	.map((file) => readFileSync(file, "utf8"))
	.join("\n");
const router = readFileSync(path.join(SRC, "router.js"), "utf8");
const serverTours = readFileSync(
	path.resolve(SRC, "../../kxcompliance/kx_compliance/tours.py"),
	"utf8"
);

// Pages without a tour of their own, and why.
const NO_TOUR = {
	Onboarding: "the setup wizard explains each step itself",
	Search: "one search box",
	ItemNew: "a form; each field is labelled",
	ItemEdit: "a form; each field is labelled",
	CompanyNew: "the company tour plays on the same page",
	SignatoryNew: "a form; each field is labelled",
	Signatory: "a form; each field is labelled",
	ItemTypeNew: "a form; each field is labelled",
	ItemType: "a form; each field is labelled",
	ObligationNew: "a form; each field is labelled",
	Obligation: "its sections say what they are",
	ClientNew: "a form; each field is labelled",
	ClientEdit: "a form; each field is labelled",
	ExtensionNew: "the extensions tour explains it",
	Extension: "the extensions tour explains it",
	RecordEvent: "a form; each field is labelled",
	NewNotice: "a form; each field is labelled",
	NewCase: "a form; each field is labelled",
	NewFiling: "a form; each field is labelled",
	NewBill: "a form; each part says what it is",
	NewTrademark: "a form; each field is labelled",
	LicenceRuleNew: "a form; each section says what it is",
	LicenceRule: "a form; each section says what it is",
	PrivacyNotice: "the notice itself, read before anything else",
	BreachNew: "a form; each section says what it is",
};

describe("tours", () => {
	it("have unique ids, each known to the server", () => {
		const ids = TOURS.map((tour) => tour.id);
		expect(new Set(ids).size).toBe(ids.length);
		const server = [...serverTours.matchAll(/^\t"([a-z-]+)",$/gm)].map((match) => match[1]);
		expect(server.sort()).toEqual([...ids].sort());
	});

	it("point only at what some page draws", () => {
		const missing = [];
		for (const tour of TOURS) {
			for (const step of tour.steps) {
				for (const name of step.target || []) {
					const found = name.startsWith("section:")
						? source.includes(`id="${name.slice("section:".length)}"`)
						: source.includes(`data-tour="${name}"`);
					if (!found) missing.push(`${tour.id}: ${name}`);
				}
			}
		}
		expect(missing).toEqual([]);
	});

	it("cover every page but those that need none", () => {
		const routes = [...new Set([...router.matchAll(/name: "([A-Za-z]+)"/g)].map((m) => m[1]))];
		const toured = new Set(TOURS.map((tour) => tour.route));
		const uncovered = routes.filter((route) => !toured.has(route) && !NO_TOUR[route]);
		expect(uncovered).toEqual([]);
		for (const tour of TOURS) expect(routes).toContain(tour.route);
	});

	it("are offered by role and kind of site", () => {
		const ids = (reader) => toursForReader(reader).map((tour) => tour.id);
		const staff = { client: false, manager: false, firm: true, checks: false };
		expect(ids(staff)).toContain("filings");
		expect(ids(staff)).not.toContain("settings");
		expect(ids(staff)).not.toContain("client-home");
		expect(ids({ ...staff, manager: true })).toContain("settings");
		expect(ids({ ...staff, firm: false })).toContain("licence-check");
		expect(ids({ ...staff, licenceCheck: false })).not.toContain("licence-check");
		expect(ids({ ...staff, licenceCheck: true })).toContain("licence-check");
		expect(ids({ ...staff, firm: false })).not.toContain("clients");
		expect(ids({ ...staff, mayBill: false })).not.toContain("billing");
		expect(ids({ ...staff, mayBill: true })).toContain("billing");
		const client = ids({ client: true, manager: false, firm: true, checks: false });
		expect(client).toContain("client-home");
		expect(client).not.toContain("bulk-filing");
		expect(ids({ client: false, manager: false, firm: false, checks: true })).toEqual([
			"licence-check",
			"account",
			"help",
		]);
	});

	it("leave out a step whose target is not on screen", () => {
		document.body.innerHTML = `<section aria-labelledby="needs-heading"><h2 id="needs-heading">Needs</h2></section>`;
		// jsdom lays nothing out, so say the section is visible and anything else is not.
		const section = document.querySelector(selectorOf("section:needs-heading"));
		section.getClientRects = () => [{}];
		const overview = TOURS.find((tour) => tour.id === "overview");
		const steps = stepsFor(overview);
		expect(steps.length).toBe(1);
		expect(steps[0].element).toBe(section);
	});

	it("speak to a client's login in a client's words, without the firm's steps", () => {
		const tour = {
			steps: [
				{
					title: "Ask the client",
					text: "Staff words",
					clientTitle: "What your firm needs",
					clientText: "Client words",
				},
				{ title: "The next step", text: "Send it for review", client: false },
			],
		};
		expect(stepsFor(tour, document, { client: true }).map((step) => step.popover)).toEqual([
			{ title: "What your firm needs", description: "Client words" },
		]);
		expect(stepsFor(tour, document, { client: false }).length).toBe(2);
	});
});
