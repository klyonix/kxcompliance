// How the app looks for this person on this device: an accent colour, row density and high
// contrast (light, dark or system is frappe-ui's own useColorScheme). Each is a data attribute
// on <html> that index.css reads; status colours never change, so red always means overdue.

export const ACCENTS = [
	{ value: "graphite", label: "Graphite", swatch: "oklch(25% 0 0)" },
	{ value: "blue", label: "Blue", swatch: "oklch(50% 0.17 255)" },
	{ value: "teal", label: "Teal", swatch: "oklch(50% 0.1 195)" },
	{ value: "green", label: "Green", swatch: "oklch(50% 0.14 150)" },
	{ value: "violet", label: "Violet", swatch: "oklch(50% 0.19 295)" },
	{ value: "orange", label: "Orange", swatch: "oklch(55% 0.17 45)" },
	{ value: "rose", label: "Rose", swatch: "oklch(52% 0.19 10)" },
];

export const DENSITIES = [
	{ value: "compact", label: "Compact" },
	{ value: "comfortable", label: "Comfortable" },
	{ value: "spacious", label: "Spacious" },
];

const KEY = "kxcompliance:appearance";
export const DEFAULTS = { accent: "graphite", density: "comfortable", contrast: "normal" };

// What was chosen on this device, with anything unknown set back to the default.
export function readAppearance(storage = localStorage) {
	let saved = {};
	try {
		saved = JSON.parse(storage.getItem(KEY) || "{}") || {};
	} catch {
		saved = {};
	}
	return {
		accent: ACCENTS.some((a) => a.value === saved.accent) ? saved.accent : DEFAULTS.accent,
		density: DENSITIES.some((d) => d.value === saved.density)
			? saved.density
			: DEFAULTS.density,
		contrast: saved.contrast === "high" ? "high" : DEFAULTS.contrast,
	};
}

export function applyAppearance(appearance, root = document.documentElement) {
	root.dataset.accent = appearance.accent;
	root.dataset.density = appearance.density;
	root.dataset.contrast = appearance.contrast;
}

export function saveAppearance(appearance, storage = localStorage, root) {
	storage.setItem(KEY, JSON.stringify(appearance));
	applyAppearance(appearance, root);
}
