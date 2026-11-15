import { describe, expect, it } from "vitest";
import { clientAttention, clientRow, clientTheme, companiesLine, yearFacts } from "./clients";

describe("a firm's clients", () => {
	it("lists a client with its lowest score and what is due", () => {
		const row = clientRow({
			name: "Mehta Traders",
			companies: ["Mehta Traders Pvt Ltd"],
			lowest_score: { score: 62, company: "Mehta Traders Pvt Ltd" },
			overdue: 1,
			due_this_week: 0,
			in_review: 0,
		});
		expect(row.status).toBe("Overdue");
		expect(row.theme).toBe("red");
		expect(row.cells).toEqual(["62 · Mehta Traders Pvt Ltd", "1 overdue"]);
		expect(row.to.params.name).toBe("Mehta Traders");
	});

	it("says what needs attention, worst first, and colours it", () => {
		const late = { overdue: 2, due_this_week: 1, in_review: 0 };
		expect(clientAttention(late)).toBe("2 overdue · 1 due this week");
		expect(clientTheme(late)).toBe("red");
		const calm = { overdue: 0, due_this_week: 0, in_review: 0 };
		expect(clientAttention(calm)).toBe("Nothing due this week");
		expect(clientTheme(calm)).toBe("green");
		expect(clientTheme({ overdue: 0, due_this_week: 0, in_review: 1 })).toBe("amber");
	});

	it("names a client's companies briefly", () => {
		expect(companiesLine([])).toBe("No companies yet");
		expect(companiesLine(["Sunrise Foods"])).toBe("Sunrise Foods");
		expect(companiesLine(["Sunrise Foods", "Sunrise Exports", "Sunrise Farms"])).toBe(
			"Sunrise Foods and 2 more"
		);
	});
});

describe("yearFacts", () => {
	const year = {
		on_time: 2,
		late: 1,
		overdue: 0,
		late_fee: 1000,
		interest: 150,
		open_cases: 1,
		waiting_on_client: 0,
		dscs_expiring: 0,
		currency: "INR",
	};

	it("gives the on-time share of the filings that fell due", () => {
		const [onTime, overdue] = yearFacts(year);
		expect(onTime).toMatchObject({ value: "67%", detail: "2 of 3 filings", tone: "amber" });
		expect(overdue).toMatchObject({ value: "0", detail: "1 filed late", tone: "gray" });
	});

	it("adds late fees and interest together", () => {
		expect(yearFacts(year)[2].value).toMatch(/1,150/);
	});

	it("speaks to the client in its own login", () => {
		expect(yearFacts(year, { client: true })[4].label).toBe("Documents your firm needs");
	});

	it("says so when nothing has fallen due yet", () => {
		const empty = { ...year, on_time: 0, late: 0, overdue: 0 };
		expect(yearFacts(empty)[0]).toMatchObject({ value: "—", tone: "gray" });
	});
});
