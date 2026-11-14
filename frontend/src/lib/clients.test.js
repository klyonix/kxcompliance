import { describe, expect, it } from "vitest";
import { clientAttention, clientTheme, companiesLine } from "./clients";

describe("a firm's clients", () => {
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
