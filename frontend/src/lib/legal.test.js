import { describe, expect, it } from "vitest";
import {
	cancelLine,
	caseRow,
	dateRow,
	markRow,
	markStatusDetails,
	nextCaseStatuses,
	nextDateError,
	outcomeValues,
	plainText,
	proceedingsError,
	referenceRoute,
} from "./legal";

const today = new Date(2026, 10, 14);

describe("legal in the app", () => {
	it("opens a date on the page of its case or trademark", () => {
		const hearing = {
			name: "LD-1",
			reference_doctype: "Legal Case",
			reference_name: "CASE-26-00001",
			reference_title: "Recovery suit",
			kind: "Hearing",
			purpose: "Arguments",
			date: "2026-11-10",
			status: "Scheduled",
			is_overdue: 1,
		};
		expect(dateRow(hearing, today)).toMatchObject({
			title: "Recovery suit",
			detail: "Hearing · Arguments",
			status: "Outcome not recorded",
			theme: "red",
			due: { text: "4 days late", late: true },
			to: { name: "LegalCase", params: { name: "CASE-26-00001" } },
		});
		expect(referenceRoute("Trademark", "TM-1")).toEqual({
			name: "Trademark",
			params: { name: "TM-1" },
		});
	});

	it("shows an open case's next date and a closed case's none", () => {
		const legalCase = {
			name: "CASE-1",
			title: "GST show cause",
			case_type: "Tax Notice or Assessment",
			forum: "Tax Officer",
			status: "Open",
			next_date: "2026-11-21",
		};
		expect(caseRow(legalCase, today)).toMatchObject({
			detail: "Tax Notice or Assessment · Tax Officer",
			theme: "blue",
			due: { text: "In 7 days" },
		});
		expect(caseRow({ ...legalCase, next_date: null }, today).due.text).toBe("No date set");
		expect(caseRow({ ...legalCase, status: "Settled" }, today)).toMatchObject({
			theme: "green",
			due: { text: "" },
		});
	});

	it("names a trademark by its application", () => {
		const mark = {
			name: "TM-1",
			mark: "KLYONIX",
			status: "Objected",
			application_number: "6123456",
		};
		expect(markRow(mark, today)).toMatchObject({
			kind: "trademark",
			detail: "Application 6123456",
			theme: "amber",
			due: { text: "No date set" },
		});
		expect(markRow({ ...mark, application_number: "" }, today).detail).toBe(
			"No application number yet"
		);
	});

	it("asks for proceedings only when a hearing went ahead or was adjourned", () => {
		expect(proceedingsError("Hearing", "Done", " ")).toBeTruthy();
		expect(proceedingsError("Hearing", "Adjourned", "Next date given")).toBeNull();
		expect(proceedingsError("Hearing", "Missed", "")).toBeNull();
		expect(proceedingsError("Reply Due", "Done", "")).toBeNull();
	});

	it("wants the next date after this one", () => {
		expect(nextDateError("2026-11-14", "2026-11-14")).toBeTruthy();
		expect(nextDateError("2026-11-14", "2026-12-02")).toBeNull();
		expect(nextDateError("2026-11-14", "")).toBeNull();
	});

	it("sends only the outcome fields that were filled in", () => {
		expect(
			outcomeValues({
				status: "Adjourned",
				attended_by: " Adv. Rao ",
				proceedings: "Adjourned at the respondent's request",
				next_date: "2026-12-02",
			})
		).toEqual({
			status: "Adjourned",
			attended_by: "Adv. Rao",
			proceedings: "Adjourned at the respondent's request",
			next_date: "2026-12-02",
		});
		expect(outcomeValues({ status: "Missed", next_date: "2026-12-02" })).toEqual({
			status: "Missed",
		});
	});

	it("reads rich text as plain text without running it", () => {
		expect(plainText("<p>Demand of <b>₹4.2 lakh</b></p><img src=x onerror=alert(1)>")).toBe(
			"Demand of ₹4.2 lakh"
		);
		expect(plainText(null)).toBe("");
	});
});

describe("moving a case on", () => {
	it("offers every status but the one it has", () => {
		expect(nextCaseStatuses("Open")).not.toContain("Open");
		expect(nextCaseStatuses("Settled")).toContain("Open");
		expect(nextCaseStatuses("Open")).toHaveLength(6);
	});
	it("says which dates closing cancels", () => {
		expect(cancelLine(0)).toBe("");
		expect(cancelLine(1)).toMatch(/^Its 1 scheduled date will be cancelled/);
		expect(cancelLine(3)).toMatch(/^Its 3 scheduled dates/);
	});
});

describe("moving a trademark on", () => {
	it("sends the stage's details that were filled in", () => {
		expect(
			markStatusDetails("Accepted and Advertised", {
				journal_number: " 2140 ",
				journal_date: "",
				registration_number: "R-1",
			})
		).toEqual({ details: { journal_number: "2140" }, missing: [] });
	});
	it("needs the number and date to register", () => {
		expect(markStatusDetails("Registered", { registration_number: "R-1" }).missing).toEqual([
			"Registration date",
		]);
		expect(markStatusDetails("Refused", {})).toEqual({ details: {}, missing: [] });
	});
});
