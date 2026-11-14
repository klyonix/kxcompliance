import { describe, expect, it } from "vitest";
import { requestRow, requestState, suggestedDueDate } from "./requests";

const today = new Date(2026, 10, 14);

describe("requestState", () => {
	it("tells the client what to do and the firm what to check", () => {
		const asked = { status: "Requested", is_overdue: 0 };
		expect(requestState(asked, { client: true }).label).toBe("To upload");
		expect(requestState(asked).label).toBe("Waiting for client");
		const uploaded = { status: "Uploaded" };
		expect(requestState(uploaded, { client: true }).label).toBe("With your firm");
		expect(requestState(uploaded)).toEqual({ label: "To check", theme: "amber" });
	});

	it("shows an overdue request in red to both", () => {
		const late = { status: "Requested", is_overdue: 1 };
		expect(requestState(late, { client: true })).toEqual({ label: "Overdue", theme: "red" });
		expect(requestState(late).theme).toBe("red");
	});
});

describe("requestRow", () => {
	it("counts down only while the client still has to send it", () => {
		const asked = {
			name: "DR-1",
			title: "Bank statement",
			status: "Requested",
			due_date: "2026-11-16",
		};
		expect(requestRow(asked, { today }).due.text).toBe("In 2 days");
		expect(requestRow({ ...asked, status: "Uploaded" }, { today }).due.text).toBe("");
		expect(requestRow(asked, { today }).to).toEqual({
			name: "DocumentRequest",
			params: { name: "DR-1" },
		});
	});
});

describe("suggestedDueDate", () => {
	it("gives a week, or the day before the filing if that is sooner", () => {
		expect(suggestedDueDate(null, today)).toBe("2026-11-21");
		expect(suggestedDueDate("2026-12-20", today)).toBe("2026-11-21");
		expect(suggestedDueDate("2026-11-18", today)).toBe("2026-11-17");
	});

	it("never suggests today or a past day", () => {
		expect(suggestedDueDate("2026-11-14", today)).toBe("2026-11-15");
	});
});
