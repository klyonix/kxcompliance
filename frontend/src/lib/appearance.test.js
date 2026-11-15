import { describe, expect, it } from "vitest";
import { ACCENTS, DEFAULTS, applyAppearance, readAppearance, saveAppearance } from "./appearance";

const memory = (value) => {
	const store = new Map(value === undefined ? [] : [["kxcompliance:appearance", value]]);
	return { getItem: (key) => store.get(key) ?? null, setItem: (key, v) => store.set(key, v) };
};

describe("how the app looks", () => {
	it("keeps known choices and falls back for anything else", () => {
		expect(readAppearance(memory())).toEqual(DEFAULTS);
		expect(readAppearance(memory("{not json"))).toEqual(DEFAULTS);
		expect(
			readAppearance(
				memory(JSON.stringify({ accent: "teal", density: "compact", contrast: "high" }))
			)
		).toEqual({ accent: "teal", density: "compact", contrast: "high" });
		expect(
			readAppearance(memory(JSON.stringify({ accent: "neon", density: "tiny" })))
		).toEqual(DEFAULTS);
	});

	it("is kept on the device and shown on the page", () => {
		const storage = memory();
		const root = { dataset: {} };
		saveAppearance(
			{ accent: "violet", density: "spacious", contrast: "normal" },
			storage,
			root
		);
		expect(readAppearance(storage).accent).toBe("violet");
		expect(root.dataset).toEqual({
			accent: "violet",
			density: "spacious",
			contrast: "normal",
		});
		applyAppearance(DEFAULTS, root);
		expect(root.dataset.accent).toBe("graphite");
	});
});

describe("accent swatches", () => {
	it("show each accent in light and in dark", () => {
		for (const accent of ACCENTS) {
			expect(accent.swatch, accent.value).toMatch(/^oklch\(/);
			expect(accent.dark, accent.value).toMatch(/^oklch\(/);
		}
	});
});
