import { describe, expect, it } from "vitest";
import { penaltyLines, scoreTone } from "./score";

describe("score", () => {
	it("colours a score", () => {
		expect([scoreTone(100), scoreTone(70), scoreTone(40), scoreTone(null)]).toEqual([
			"green",
			"amber",
			"red",
			"gray",
		]);
	});
});

describe("penaltyLines", () => {
	const base = { counted: true, late_fee: 0, late_fee_in_a_week: 0, days_late: 0, days_left: 0 };

	it("says what lateness has cost and will cost", () => {
		const lines = penaltyLines({
			...base,
			days_late: 12,
			late_fee: 600,
			late_fee_in_a_week: 950,
			interest_percent: 18,
		});
		expect(lines[0]).toMatch(/^Late fee so far: .*600 \(12 days late\)\.$/);
		expect(lines[1]).toMatch(/950/);
		expect(lines[2]).toBe("Plus interest at 18% a year on tax paid late.");
	});

	it("warns before the due date when a week's delay would cost", () => {
		expect(penaltyLines({ ...base, days_left: 5, late_fee_in_a_week: 100 })[0]).toMatch(/100/);
		expect(penaltyLines({ ...base, days_left: 20 })).toEqual([
			"No late fee if it is filed by the due date.",
		]);
	});

	it("gives only the interest where the rule has no fixed fee", () => {
		expect(penaltyLines({ ...base, counted: false, interest_percent: 12 })).toEqual([
			"Plus interest at 12% a year on tax paid late.",
		]);
	});
});
