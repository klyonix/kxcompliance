import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
	REPORTS,
	clientDefaults,
	filledFilters,
	financialYear,
	initialFilters,
	linkRoute,
	matchReports,
	missingRequired,
	recentReports,
	rememberOpened,
	reportBySlug,
	reportsFor,
	rowsOf,
	sortRows,
	splitTotal,
	toCsv,
} from "./reports";

const REPORT_DIR = path.resolve(import.meta.dirname, "../../../kxcompliance/kx_compliance/report");

describe("the reports", () => {
	it("are the Desk's reports, with the Desk's filters", () => {
		const desk = readdirSync(REPORT_DIR).filter((name) => !name.startsWith("_"));
		expect(REPORTS.length).toBe(desk.length);
		for (const report of REPORTS) {
			const folder = report.name.toLowerCase().replace(/[ -]/g, "_");
			const script = readFileSync(path.join(REPORT_DIR, folder, `${folder}.js`), "utf8");
			for (const filter of report.filters) {
				expect(script, `${report.name}: ${filter.fieldname}`).toContain(
					`fieldname: "${filter.fieldname}"`
				);
			}
		}
	});

	it("are offered by kind of site and role", () => {
		const slugs = (reader) => reportsFor(reader).map((report) => report.slug);
		const staff = { firm: true, manager: false, auditor: false };
		expect(slugs(staff)).toContain("client-summary");
		expect(slugs(staff)).not.toContain("contingent-liabilities");
		expect(slugs(staff)).not.toContain("party-licence-register");
		expect(slugs({ ...staff, auditor: true })).toContain("contingent-liabilities");
		expect(slugs({ ...staff, firm: false })).toContain("party-licence-register");
		expect(slugs({ ...staff, firm: false })).not.toContain("client-summary");
		// The firm's bills, only for those who may bill.
		expect(slugs(staff)).not.toContain("billing-outstanding");
		expect(slugs({ ...staff, bills: true })).toEqual(
			expect.arrayContaining(["billing-outstanding", "billing-by-month", "unbilled-filings"])
		);
	});

	it("open with the address's filters over their defaults", () => {
		const today = new Date(2027, 1, 10);
		expect(financialYear(today)).toEqual({ start: "2026-04-01", end: "2027-03-31" });
		expect(financialYear(new Date(2026, 3, 1)).start).toBe("2026-04-01");
		const summary = reportBySlug("client-summary");
		expect(initialFilters(summary, { client: "Sunrise Group" }, today)).toEqual({
			from_date: "2026-04-01",
			to_date: "2027-03-31",
			client: "Sunrise Group",
			relationship_manager: "",
		});
		const legal = reportBySlug("legal-calendar");
		expect(initialFilters(legal, {}, today).to_date).toBe("2027-03-12");
		expect(
			missingRequired(legal, { from_date: "2027-02-10" }).map((f) => f.fieldname)
		).toEqual(["to_date"]);
		expect(filledFilters({ a: "x", b: "", c: null })).toEqual({ a: "x" });
	});

	it("show results as the Desk does", () => {
		const columns = [
			{ fieldname: "name", label: "Case", fieldtype: "Link", options: "Legal Case" },
			{ fieldname: "late_fee", label: "Late Fees", fieldtype: "Currency" },
			{ fieldname: "on_time_percent", label: "On Time %", fieldtype: "Percent" },
		];
		const rows = rowsOf(
			[["LC-2", 200, 50], { name: "LC-10", late_fee: 50, on_time_percent: 100 }],
			columns
		);
		expect(rows[0]).toEqual({ name: "LC-2", late_fee: 200, on_time_percent: 50 });
		expect(sortRows(rows, "name").map((row) => row.name)).toEqual(["LC-2", "LC-10"]);
		expect(sortRows(rows, "late_fee", true).map((row) => row.late_fee)).toEqual([200, 50]);
		expect(splitTotal(rows, true)).toEqual({ rows: [rows[0]], total: rows[1] });
		expect(splitTotal(rows, false).total).toBeNull();
		expect(linkRoute(columns[0], "LC-2")).toEqual({
			name: "LegalCase",
			params: { name: "LC-2" },
		});
		expect(linkRoute({ fieldtype: "Link", options: "Supplier" }, "X")).toBeNull();
		expect(toCsv(columns.slice(0, 2), [{ name: 'A, "B"', late_fee: 5 }])).toBe(
			'Case,Late Fees\n"A, ""B""",5'
		);
	});
});

describe("finding a report", () => {
	const all = reportsFor({ firm: true, manager: true, auditor: false });

	it("matches every word typed, in any order, in the title or its line", () => {
		expect(matchReports(all, "").length).toBe(all.length);
		expect(matchReports(all, "on-time filing").map((report) => report.slug)).toContain(
			all.find((report) => report.title === "On-time filing").slug
		);
		expect(matchReports(all, "nothing like this")).toEqual([]);
	});

	it("keeps the reports opened lately, newest first, three at most", () => {
		const store = new Map();
		const storage = {
			getItem: (key) => store.get(key) ?? null,
			setItem: (key, value) => store.set(key, value),
		};
		for (const report of all.slice(0, 4)) rememberOpened(report.slug, storage);
		rememberOpened(all[1].slug, storage);
		expect(recentReports(all, storage).map((report) => report.slug)).toEqual([
			all[1].slug,
			all[3].slug,
			all[2].slug,
		]);
	});

	it("shrugs off a damaged list", () => {
		const storage = { getItem: () => "{not json", setItem: () => {} };
		expect(recentReports(all, storage)).toEqual([]);
	});
});

describe("a report opened with one client chosen", () => {
	const byClient = { filters: [{ fieldname: "client" }, { fieldname: "company" }] };
	const byCompany = { filters: [{ fieldname: "company" }] };
	const chosen = { client: "Sunrise Group", companies: ["Sunrise Foods"] };

	it("starts on that client, or on its only company", () => {
		expect(clientDefaults(byClient, {}, chosen)).toEqual({ client: "Sunrise Group" });
		expect(clientDefaults(byCompany, {}, chosen)).toEqual({ company: "Sunrise Foods" });
	});

	it("leaves a client of several companies, the address and no client alone", () => {
		expect(clientDefaults(byCompany, {}, { ...chosen, companies: ["A", "B"] })).toEqual({});
		expect(clientDefaults(byClient, { client: "" }, chosen)).toEqual({});
		expect(clientDefaults(byClient, {}, {})).toEqual({});
	});
});
