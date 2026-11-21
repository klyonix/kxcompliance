import { describe, expect, it } from "vitest";
import {
	returnGroups,
	changedValues,
	filingSteps,
	formValues,
	hasFilingDetails,
	missingDetails,
	nilDeclared,
	showFilingForm,
	taskActions,
	taskRow,
	taskTheme,
} from "./filings";

const today = new Date(2026, 10, 14);
const task = {
	name: "CT-26-00012",
	obligation_template: "GSTR-3B (Monthly)",
	period_label: "Oct 2026",
	company: "Demo Industries",
	status: "Open",
	is_overdue: 0,
	effective_due_date: "2026-11-20",
	responsible: "asha@example.com",
	reviewer: "ravi@example.com",
};
const reviewed = { requires_review: 1, requires_proof: 1 };
const as = (user, role = "Compliance User") => ({ user, roles: [role] });

describe("filings in the app", () => {
	it("turns a task into a row that opens its filing page", () => {
		expect(taskRow(task, today)).toMatchObject({
			kind: "filing",
			title: "GSTR-3B (Monthly)",
			detail: "Oct 2026 · Demo Industries",
			theme: "gray",
			due: { text: "In 6 days", late: false },
			to: { name: "ComplianceTask", params: { name: "CT-26-00012" } },
		});
		const late = { ...task, is_overdue: 1, effective_due_date: "2026-11-11" };
		expect(taskRow(late, today)).toMatchObject({
			theme: "red",
			due: { text: "3 days late", late: true },
		});
		const filed = { ...task, status: "Filed", filed_on: "2026-11-18" };
		expect(taskRow(filed, today).due.text).toMatch(/^Filed /);
		expect(taskRow({ ...task, status: "Not Applicable" }, today).due.text).toBe("");
	});

	it("colours a status by how pressing it is", () => {
		expect(taskTheme("Ready for Review", false)).toBe("amber");
		expect(taskTheme("Filed", false)).toBe("green");
		expect(taskTheme("In Progress", true)).toBe("red");
	});

	it("has the preparer send a reviewed filing for review, and the reviewer mark it filed", () => {
		expect(taskActions(task, reviewed, as("asha@example.com"))).toEqual({
			edit: true,
			sendForReview: true,
			markFiled: false,
			sendBack: false,
		});
		const inReview = { ...task, status: "Ready for Review" };
		expect(taskActions(inReview, reviewed, as("asha@example.com"))).toMatchObject({
			sendForReview: false,
			markFiled: false,
		});
		expect(taskActions(inReview, reviewed, as("ravi@example.com"))).toMatchObject({
			markFiled: true,
			sendBack: true,
		});
		expect(
			taskActions(inReview, reviewed, as("meera@example.com", "Compliance Manager"))
		).toMatchObject({ markFiled: true, sendBack: true });
	});

	it("lets a manager with no one to check their filing mark it filed", () => {
		const alone = { ...task, responsible: "priya@example.com", reviewer: null };
		const manager = as("priya@example.com", "Compliance Manager");
		expect(taskActions(alone, reviewed, manager)).toEqual({
			edit: true,
			sendForReview: false,
			markFiled: true,
			sendBack: false,
		});
		expect(
			taskActions({ ...alone, status: "Ready for Review" }, reviewed, manager)
		).toMatchObject({
			markFiled: true,
		});
		// With a checker set, or without the manager role, someone else still checks it.
		expect(
			taskActions({ ...alone, reviewer: "ravi@example.com" }, reviewed, manager)
		).toMatchObject({ sendForReview: true, markFiled: false });
		expect(taskActions(alone, reviewed, as("priya@example.com"))).toMatchObject({
			sendForReview: true,
			markFiled: false,
		});
	});

	it("lets the responsible person mark a filing filed when it needs no review", () => {
		expect(taskActions(task, { requires_review: 0 }, as("asha@example.com"))).toMatchObject({
			sendForReview: false,
			markFiled: true,
		});
	});

	it("lets nobody else act, and nobody act on a closed filing", () => {
		expect(taskActions(task, reviewed, as("meera@example.com")).edit).toBe(false);
		expect(
			taskActions(task, reviewed, as("meera@example.com", "Compliance Auditor")).edit
		).toBe(false);
		const filed = { ...task, status: "Filed" };
		expect(
			taskActions(filed, reviewed, as("meera@example.com", "Compliance Manager")).edit
		).toBe(false);
		expect(taskActions(task, null, as("asha@example.com")).edit).toBe(false);
	});

	it("names the details still missing before review or filing", () => {
		expect(missingDetails({ acknowledgement_number: "  " }, reviewed)).toEqual([
			"Filed on",
			"Acknowledgement number",
			"Proof",
		]);
		expect(
			missingDetails(
				{ filed_on: "2026-11-18", acknowledgement_number: "AA2911" },
				reviewed,
				{ proofWaiting: true }
			)
		).toEqual([]);
		expect(
			missingDetails({ filed_on: "2026-11-18", acknowledgement_number: "AA2911" }, {})
		).toEqual([]);
	});

	it("asks only for the date of a NIL period that gives no acknowledgement", () => {
		const tds = { allows_nil: 1, nil_needs_acknowledgement: 0, requires_proof: 1 };
		const gst = { allows_nil: 1, nil_needs_acknowledgement: 1, requires_proof: 1 };
		expect(nilDeclared({ is_nil: 1 }, tds)).toBe(true);
		expect(nilDeclared({ is_nil: 0 }, tds)).toBe(false);
		expect(nilDeclared({ is_nil: 1 }, gst)).toBe(false);
		expect(missingDetails({ is_nil: true }, tds)).toEqual(["Filed on"]);
		expect(missingDetails({ is_nil: true, filed_on: "2026-11-18" }, tds)).toEqual([]);
		expect(missingDetails({ is_nil: true, filed_on: "2026-11-18" }, gst)).toEqual([
			"Acknowledgement number",
			"Proof",
		]);
	});

	it("sends the NIL tick as 0 or 1, and only when it changed", () => {
		const saved = { is_nil: 0, filed_on: "" };
		const form = formValues(saved);
		expect(form.is_nil).toBe(false);
		expect(changedValues(form, saved)).toEqual({});
		expect(changedValues({ ...form, is_nil: true }, saved)).toEqual({ is_nil: 1 });
		expect(
			changedValues({ ...formValues({ is_nil: 1 }), is_nil: false }, { is_nil: 1 })
		).toEqual({ is_nil: 0 });
	});

	it("sends only the details that changed, and an emptied one as empty", () => {
		const saved = { filed_on: "2026-11-18", acknowledgement_number: "AA2911", amount_paid: 0 };
		const form = { ...formValues(saved), acknowledgement_number: "AA2912" };
		expect(form.amount_paid).toBe("");
		expect(changedValues(form, saved)).toEqual({ acknowledgement_number: "AA2912" });
		expect(changedValues({ ...form, amount_paid: "1250.50" }, saved)).toMatchObject({
			amount_paid: 1250.5,
		});
		expect(changedValues({ ...saved, filed_on: "" }, saved)).toEqual({ filed_on: null });
	});
});

describe("a time-barred filing in the list", () => {
	it("says so in place of how late it is, until it is closed", () => {
		const task = {
			name: "CT-OLD",
			obligation_template: "GSTR-1 (Monthly)",
			period_label: "Oct 2023",
			company: "Demo Industries",
			status: "Open",
			is_overdue: 1,
			effective_due_date: "2023-11-11",
			is_time_barred: 1,
			last_filing_date: "2026-11-11",
		};
		expect(taskRow(task, new Date(2026, 10, 21)).due).toEqual({
			text: "Time-barred",
			late: true,
		});
		expect(taskRow({ ...task, status: "Not Applicable", is_time_barred: 0 }).due.text).toBe(
			""
		);
	});
});

describe("the filing page's steps", () => {
	const reviewed = { requires_review: 1 };

	it("shows Review only where the return needs one, and where the filing is", () => {
		expect(filingSteps({ status: "Open" }, reviewed)).toEqual({
			steps: ["File", "Review", "Filed"],
			current: 0,
		});
		expect(filingSteps({ status: "Ready for Review" }, reviewed).current).toBe(1);
		expect(filingSteps({ status: "Filed Late" }, reviewed).current).toBe(2);
		expect(filingSteps({ status: "In Progress" }, {})).toEqual({
			steps: ["File", "Filed"],
			current: 0,
		});
	});

	it("opens the filing fields when asked, or when something is already recorded", () => {
		const open = { status: "Open" };
		expect(showFilingForm(open, { editable: true, opened: false })).toBe(false);
		expect(showFilingForm(open, { editable: true, opened: true })).toBe(true);
		expect(
			showFilingForm(
				{ status: "In Progress", acknowledgement_number: "AA1" },
				{ editable: true, opened: false }
			)
		).toBe(true);
		expect(
			showFilingForm(
				{ status: "Open", remarks: "client slow" },
				{ editable: true, opened: false }
			)
		).toBe(false);
		expect(hasFilingDetails({ amount_paid: "0", interest: 0 })).toBe(false);
		expect(hasFilingDetails({ late_fee: 200 })).toBe(true);
	});

	it("keeps a filing in review folded until someone corrects it, and closed ones shut", () => {
		const review = { status: "Ready for Review", acknowledgement_number: "AA1" };
		expect(showFilingForm(review, { editable: true, opened: false })).toBe(false);
		expect(showFilingForm(review, { editable: true, opened: true })).toBe(true);
		expect(showFilingForm({ status: "Filed" }, { editable: true, opened: true })).toBe(false);
		expect(showFilingForm({ status: "Open" }, { editable: false, opened: true })).toBe(false);
	});
});

describe("the library as a choice of return", () => {
	it("groups returns by law, with their form when it differs", () => {
		expect(
			returnGroups([
				{ name: "GSTR-3B (Monthly)", law: "GST", form: "GSTR-3B" },
				{ name: "Annual Return", law: "Companies Act", form: "MGT-7" },
				{ name: "Shop licence", law: "" },
			])
		).toEqual([
			{
				group: "Companies Act",
				options: [{ label: "Annual Return (MGT-7)", value: "Annual Return" }],
			},
			{
				group: "GST",
				options: [{ label: "GSTR-3B (Monthly)", value: "GSTR-3B (Monthly)" }],
			},
			{ group: "Other", options: [{ label: "Shop licence", value: "Shop licence" }] },
		]);
	});
});
