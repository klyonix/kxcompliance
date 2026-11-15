import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { ARTICLES } from "@/help/articles";
import hi from "./hi";

const SRC = path.resolve(import.meta.dirname, "..");
// The screens and parts a client's login sees, whose phrases are all translated.
const CLIENT_FILES = [
	"App.vue",
	"components/AppSidebar.vue",
	"components/NotificationBell.vue",
	"components/AppPageHeader.vue",
	"components/RecordList.vue",
	"components/WorkRow.vue",
	"components/PrivacySection.vue",
	"components/BillingCard.vue",
	"components/StatementDialog.vue",
	"pages/myWork.js",
	"lib/clients.js",
	"lib/items.js",
	"pages/Client.vue",
	"pages/DocumentRequest.vue",
	"pages/Account.vue",
	"pages/PrivacyNotice.vue",
	"pages/Help.vue",
];
const PHRASE = /\bt\(\s*("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/g;

describe("Hindi for client logins", () => {
	it("translates every phrase the client screens write", () => {
		const missing = [];
		for (const file of CLIENT_FILES) {
			const source = readFileSync(path.join(SRC, file), "utf8");
			for (const match of source.matchAll(PHRASE)) {
				const phrase = match[1].slice(1, -1).replace(/\\"/g, '"').replace(/\\'/g, "'");
				if (!hi[phrase]) missing.push(`${file}: ${phrase}`);
			}
		}
		expect(missing).toEqual([]);
	});

	it("translates the client's menu and the help answers they see", () => {
		const missing = [];
		for (const label of [
			"Search",
			"Home",
			"Filings",
			"Register",
			"Legal",
			"Help",
			"Account",
		]) {
			if (!hi[label]) missing.push(label);
		}
		for (const article of ARTICLES.filter((entry) => entry.client)) {
			for (const phrase of [
				article.area,
				article.title,
				article.when,
				...article.steps,
				article.tip,
			]) {
				if (phrase && !hi[phrase]) missing.push(`${article.id}: ${phrase}`);
			}
		}
		expect(missing).toEqual([]);
	});

	it("keeps the numbers each phrase has", () => {
		const wrong = Object.entries(hi).filter(
			([english, hindi]) =>
				(english.match(/\{\d\}/g) || []).sort().join() !==
				(hindi.match(/\{\d\}/g) || []).sort().join()
		);
		expect(wrong).toEqual([]);
	});
});
