// Every colour token class and icon the app uses must exist in frappe-ui's theme; a class
// that does not exist is dropped by Tailwind without a word, and the screen silently loses
// its background, border or icon.
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { pathToFileURL } from "node:url";

const SRC = path.resolve(import.meta.dirname);
const files = (dir) =>
	readdirSync(dir).flatMap((name) => {
		const full = path.join(dir, name);
		if (statSync(full).isDirectory()) return files(full);
		return /\.(vue|js)$/.test(name) && !name.endsWith(".test.js") ? [full] : [];
	});

const BADGE_THEMES = ["gray", "blue", "green", "amber", "red", "violet"];

// The light theme's token names, e.g. surface.base, ink.gray-9, outline.gray-1. frappe-ui does
// not export this file by name, so it is read from where the package installs it.
const coloursFile = path.resolve(SRC, "../node_modules/frappe-ui/tailwind/tokens/colors.js");
const colours = await import(pathToFileURL(coloursFile).href);
const tokens = (colours.default || colours).themedVariables.light;

function tokenExists(token) {
	const [, group, name] = token.match(/^(surface|ink|outline)-(.+)$/) || [];
	return Boolean(group && Object.prototype.hasOwnProperty.call(tokens[group], name));
}

describe("style classes", () => {
	const source = files(SRC).map((file) => [file, readFileSync(file, "utf8")]);

	it("only uses colour tokens frappe-ui defines", () => {
		const missing = [];
		for (const [file, text] of source) {
			for (const [, prefix, token] of text.matchAll(
				/\b(bg|text|border)-((?:surface|ink|outline)-[a-z]+(?:-[a-z0-9]+)*)\b/g
			)) {
				if (!tokenExists(token))
					missing.push(`${path.relative(SRC, file)}: ${prefix}-${token}`);
			}
		}
		expect(missing).toEqual([]);
	});

	it("never uses divide colours, which this preset does not generate", () => {
		const offenders = source
			.filter(([, text]) => /\bdivide-(surface|ink|outline)-/.test(text))
			.map(([file]) => file);
		expect(offenders).toEqual([]);
	});

	it("only asks Badge for themes it has", () => {
		// The badge colour is chosen in each file's themeFor(); read the returns inside it.
		const bodies = source.flatMap(([, text]) =>
			[...text.matchAll(/function themeFor\([^)]*\) \{([\s\S]*?)\n\}/g)].map(
				(match) => match[1]
			)
		);
		expect(bodies.length).toBeGreaterThan(0);
		const themes = bodies.flatMap((body) =>
			[...body.matchAll(/return '([a-z]+)'/g)].map((match) => match[1])
		);
		expect(themes.filter((theme) => !BADGE_THEMES.includes(theme))).toEqual([]);
	});
});
