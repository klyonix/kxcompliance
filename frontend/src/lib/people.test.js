import { describe, expect, it } from "vitest";
import { personOptions } from "./people";

describe("personOptions", () => {
	it("names people, and adds the email only where names repeat", () => {
		expect(
			personOptions([
				{ name: "Administrator", full_name: "Administrator" },
				{ name: "admin@example.com", full_name: "Administrator" },
				{ name: "asha@example.com", full_name: "Asha Rao" },
				{ name: "nobody@example.com", full_name: "" },
			]).map((option) => option.label)
		).toEqual([
			"Administrator",
			"Administrator (admin@example.com)",
			"Asha Rao",
			"nobody@example.com",
		]);
	});
});
