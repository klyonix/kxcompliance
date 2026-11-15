import { describe, expect, it } from "vitest";
import {
	boardDeadline,
	boardHoursLeft,
	breachRow,
	isMasked,
	requestRow,
	safeNext,
} from "./privacy";

const NOW = new Date("2026-11-15T10:00:00");

describe("a breach's deadline at the Board", () => {
	it("counts the hours left, then the hours late, and stops once reported", () => {
		const breach = { board_due_by: "2026-11-15 15:00:00" };
		expect(boardHoursLeft(breach, NOW)).toBe(5);
		expect(boardDeadline(breach, NOW)).toBe("Report to the Board within 5 hours");
		expect(
			breachRow({ ...breach, title: "Lost laptop", status: "Board not told" }, NOW).due
		).toEqual({
			text: "5h left",
			late: false,
		});
		const late = { board_due_by: "2026-11-15 07:00:00" };
		expect(boardDeadline(late, NOW)).toBe("The Board's report is 3 hours late");
		expect(breachRow({ ...late, status: "Board not told" }, NOW).due).toEqual({
			text: "3h late",
			late: true,
		});
		expect(boardDeadline({ ...late, board_reported_on: "2026-11-15 06:00:00" }, NOW)).toBe("");
	});
});

describe("privacy requests", () => {
	it("are late once their 90 days have passed", () => {
		const row = requestRow(
			{
				name: "PRQ-26-00001",
				request_type: "Grievance",
				requester_name: "Neha",
				status: "Open",
				due_by: "2026-11-14",
			},
			NOW
		);
		expect(row.title).toBe("Grievance: Neha");
		expect(row.due.late).toBe(true);
	});
});

describe("masking and the way back", () => {
	it("knows a masked PAN or mobile", () => {
		expect(isMasked("XXXXXXXX")).toBe(true);
		expect(isMasked("987XXXXXX")).toBe(true);
		expect(isMasked("ABCDE1234F")).toBe(false);
		expect(isMasked("")).toBe(false);
	});

	it("goes back only to a page of this app", () => {
		expect(safeNext("/filings?view=open")).toBe("/filings?view=open");
		expect(safeNext("//evil.example")).toBe("/");
		expect(safeNext("https://evil.example")).toBe("/");
		expect(safeNext(undefined)).toBe("/");
	});
});
