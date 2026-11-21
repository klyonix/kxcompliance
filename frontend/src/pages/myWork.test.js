import { describe, expect, it } from "vitest";
import { relativeDue, summarise, timeBarDue, workRows } from "./myWork";

const today = new Date(2026, 10, 14);

const rows = workRows(
	{
		items: [
			{
				name: "CI-1",
				title: "Fire NOC, Peenya plant",
				item_type: "Fire NOC",
				status: "Expired",
				valid_until: "2026-11-01",
			},
			{
				name: "CI-2",
				title: "Trade licence, Pune",
				item_type: "Trade Licence",
				status: "Due for Renewal",
				valid_until: "2026-12-10",
			},
		],
		tasks: [
			{
				name: "CT-1",
				obligation_template: "GSTR-3B (Monthly)",
				period_label: "Oct 2026",
				company: "Demo",
				status: "Open",
				is_overdue: 0,
				effective_due_date: "2026-11-20",
			},
		],
		legal_dates: [
			{
				name: "LD-1",
				kind: "Hearing",
				date: "2026-11-10",
				reference_doctype: "Legal Case",
				reference_name: "CASE-1",
				reference_title: "Recovery suit",
				is_overdue: 1,
			},
		],
	},
	{ today }
);

describe("My Work rows", () => {
	it("lists everything soonest first and links each row to its record", () => {
		expect(rows.map((row) => row.key)).toEqual([
			"item-CI-1",
			"legal-LD-1",
			"task-CT-1",
			"item-CI-2",
		]);
		expect(rows[1].to).toEqual({ name: "LegalCase", params: { name: "CASE-1" } });
		expect(rows[0].to).toEqual({ name: "ComplianceItem", params: { name: "CI-1" } });
		expect(rows[2].to).toEqual({ name: "ComplianceTask", params: { name: "CT-1" } });
	});

	it("puts each row in a bucket and says when it is due", () => {
		const byKey = Object.fromEntries(rows.map((row) => [row.key, row]));
		expect(byKey["item-CI-1"]).toMatchObject({
			bucket: "overdue",
			theme: "red",
			due: { text: "13 days late", late: true },
		});
		expect(byKey["legal-LD-1"]).toMatchObject({
			bucket: "overdue",
			status: "Outcome not recorded",
			due: { text: "4 days late" },
		});
		expect(byKey["task-CT-1"]).toMatchObject({
			bucket: "week",
			due: { text: "In 6 days", late: false },
		});
		expect(byKey["item-CI-2"]).toMatchObject({
			bucket: "later",
			theme: "amber",
			due: { text: "In 26 days" },
		});
	});

	it("counts each bucket", () => {
		expect(summarise(rows)).toEqual({ overdue: 2, week: 1, later: 1 });
	});
});

describe("relative due dates", () => {
	it("reads naturally around today", () => {
		expect(relativeDue("2026-11-14", today).text).toBe("Today");
		expect(relativeDue("2026-11-15", today).text).toBe("Tomorrow");
		expect(relativeDue("2026-11-13", today).text).toBe("1 day late");
		expect(relativeDue(null, today).text).toBe("No date");
	});
});

describe("the GST time-bar", () => {
	const late = { status: "Open", is_overdue: 1, effective_due_date: "2023-12-20" };

	it("says a filing is time-barred once its last day to file has passed", () => {
		expect(
			timeBarDue({ ...late, is_time_barred: 1, last_filing_date: "2026-11-01" }, today)
		).toEqual({ text: "Time-barred", late: true });
	});

	it("names the last day to file in the 90 days before it, and not earlier", () => {
		const near = timeBarDue({ ...late, last_filing_date: "2027-02-11" }, today);
		expect(near.late).toBe(true);
		expect(near.text).toMatch(/^Last day to file .*2027/);
		expect(timeBarDue({ ...late, last_filing_date: "2027-02-13" }, today)).toBeNull();
		const inReview = { ...late, status: "Ready for Review", last_filing_date: "2027-02-11" };
		expect(timeBarDue(inReview, today)).toBeNull();
		expect(timeBarDue({ is_overdue: 0, effective_due_date: "2026-12-20" }, today)).toBeNull();
	});

	it("shows it in My Work in place of how late the filing is", () => {
		const [row] = workRows(
			{
				items: [],
				tasks: [
					{
						name: "CT-OLD",
						obligation_template: "GSTR-3B (Monthly)",
						period_label: "Nov 2023",
						company: "Demo Industries",
						...late,
						is_time_barred: 1,
						last_filing_date: "2026-11-01",
					},
				],
				legal_dates: [],
			},
			{ today }
		);
		expect(row.due).toEqual({ text: "Time-barred", late: true });
		expect(row.bucket).toBe("overdue");
	});
});
