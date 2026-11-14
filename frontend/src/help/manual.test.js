// The manual names buttons and tabs in double quotes, as the screens show them; a renamed button
// would leave an answer pointing at nothing, so every quoted name must be in the app's source.
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { tourFor } from "@/tours/tours";
import { toursForReader } from "@/tours/useTours";
import { AREAS, ARTICLES } from "./articles";
import { articlesFor, groupArticles } from "./manual";

const SRC = path.resolve(import.meta.dirname, "..");
const files = (dir) =>
	readdirSync(dir).flatMap((name) => {
		const full = path.join(dir, name);
		if (statSync(full).isDirectory()) return files(full);
		return /\.(vue|js)$/.test(name) && !/\.test\.js$|articles\.js$/.test(name) ? [full] : [];
	});
const source = files(SRC)
	.map((file) => readFileSync(file, "utf8"))
	.join("\n");

const reader = (flags) => ({ ...flags, tours: toursForReader({ checks: false, ...flags }) });

describe("the user manual", () => {
	it("names only buttons and tabs the app has", () => {
		const missing = [];
		for (const article of ARTICLES) {
			for (const text of [...article.steps, article.tip || ""]) {
				for (const [, name] of text.matchAll(/"([^"]+)"/g)) {
					if (!source.includes(`"${name}"`) && !source.includes(`'${name}'`))
						missing.push(`${article.id}: "${name}"`);
				}
			}
		}
		expect(missing).toEqual([]);
	});

	it("has unique answers, each in a known area, about a page that exists", () => {
		const ids = ARTICLES.map((article) => article.id);
		expect(new Set(ids).size).toBe(ids.length);
		for (const article of ARTICLES) {
			expect(AREAS).toContain(article.area);
			expect(tourFor(article.page), article.id).toBeTruthy();
		}
	});

	it("shows each person the answers for what they do", () => {
		const ids = (flags) => articlesFor(reader(flags)).map((article) => article.id);
		const staff = ids({ client: false, manager: false, firm: true });
		expect(staff).toContain("file-a-return");
		expect(staff).not.toContain("invite-a-colleague");
		expect(staff).not.toContain("client-upload");
		expect(ids({ client: false, manager: true, firm: true })).toContain("invite-a-colleague");
		expect(ids({ client: false, manager: false, firm: false })).not.toContain(
			"ask-the-client"
		);
		const client = ids({ client: true, manager: false, firm: true });
		expect(client).toEqual(["client-upload", "client-see-work"]);
	});

	it("finds answers by every word typed", () => {
		const all = articlesFor(reader({ client: false, manager: true, firm: true }));
		const found = groupArticles(all, "extend date").flatMap((group) => group.articles);
		expect(found.map((article) => article.id)).toEqual(["extend-a-due-date"]);
		expect(groupArticles(all, "")[0].area).toBe("Getting started");
	});
});
