import { describe, expect, it } from "vitest";
import { googleLink, outlookLink, webcal } from "./calendarFeed";

const url = "https://firm.example.com/api/method/x.feed?token=abc";

describe("calendar links", () => {
	it("offers the feed as a webcal link", () => {
		expect(webcal(url)).toBe("webcal://firm.example.com/api/method/x.feed?token=abc");
	});

	it("opens Google Calendar with the feed", () => {
		expect(googleLink(url)).toBe(
			"https://calendar.google.com/calendar/r?cid=webcal%3A%2F%2Ffirm.example.com%2Fapi%2Fmethod%2Fx.feed%3Ftoken%3Dabc"
		);
	});

	it("opens Outlook with the feed and its name", () => {
		const link = new URL(outlookLink(url, "Rao & Associates"));
		expect(link.searchParams.get("url")).toBe(url);
		expect(link.searchParams.get("name")).toBe("Rao & Associates");
	});
});
