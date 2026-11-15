import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { ARTICLES } from "./articles";
import { userGuide } from "./guide";

const GUIDE = path.resolve(import.meta.dirname, "../../../USER_GUIDE.md");

describe("the public user guide", () => {
	it("is the app's Help, rebuilt after every change (node scripts/user-guide.mjs)", () => {
		expect(readFileSync(GUIDE, "utf8")).toBe(userGuide());
	});

	it("has every answer, and says who each is for", () => {
		const guide = userGuide();
		for (const article of ARTICLES) expect(guide).toContain(`### ${article.title}`);
		expect(guide).toContain("*For: Managers.*");
		expect(guide).toContain("*For: Client logins.*");
	});
});
