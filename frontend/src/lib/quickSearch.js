// Quick search (Ctrl/⌘ K): the box that opens over any page, the pages and actions it can jump
// to, and the searches a person ran lately (kept on this device only).
import { ref } from "vue";
import { boot, isManager, mayRecord } from "@/boot";
import { sections, settingsPagesFor } from "@/navigation";

export const paletteOpen = ref(false);

const RECENT_KEY = "kxcompliance:recent-searches";
const RECENT_LIMIT = 5;

export const shortcutLabel = (platform = globalThis.navigator?.platform || "") =>
	/mac|iphone|ipad/i.test(platform) ? "⌘K" : "Ctrl+K";

export function recentSearches(storage = globalThis.localStorage) {
	try {
		const saved = JSON.parse(storage?.getItem(RECENT_KEY) || "[]");
		return Array.isArray(saved) ? saved.filter((entry) => typeof entry === "string") : [];
	} catch {
		return [];
	}
}

// The words searched, first, once, and only the last few.
export function rememberSearch(text, storage = globalThis.localStorage) {
	const query = String(text || "").trim();
	if (query.length < 2 || !storage) return;
	const kept = [query, ...recentSearches(storage).filter((entry) => entry !== query)];
	storage.setItem(RECENT_KEY, JSON.stringify(kept.slice(0, RECENT_LIMIT)));
}

// Where the box can jump without searching: the person's own menu, Settings for managers, and
// the things they can start.
export function goToItems({
	menu = sections,
	settings = isManager() ? settingsPagesFor() : [],
	manager = isManager(),
	records = mayRecord(),
	firm = boot.accountType === "CA/CS Firm",
} = {}) {
	const pages = [...menu.filter((section) => section.route !== "Search"), ...settings].map(
		(page) => ({
			key: `page-${page.route}`,
			group: "Go to",
			label: page.label,
			icon: page.icon,
			to: { name: page.route },
		})
	);
	const actions = [
		records && { label: "New register item", icon: "lucide-plus", route: "ItemNew" },
		records && { label: "Log a notice", icon: "lucide-scale", route: "NewNotice" },
		records && { label: "Start a case", icon: "lucide-gavel", route: "NewCase" },
		records && { label: "Add a trademark", icon: "lucide-stamp", route: "NewTrademark" },
		records && {
			label: "Record an event",
			icon: "lucide-calendar-plus",
			route: "RecordEvent",
		},
		records && { label: "Add a signatory", icon: "lucide-pen-line", route: "SignatoryNew" },
		manager && firm && { label: "Add a client", icon: "lucide-user-plus", route: "ClientNew" },
		manager && {
			label: "File in bulk",
			icon: "lucide-list-checks",
			route: "BulkFiling",
		},
	]
		.filter(Boolean)
		.map((action) => ({
			key: `action-${action.route}`,
			group: "Create",
			label: action.label,
			icon: action.icon,
			to: { name: action.route },
		}));
	return [...pages, ...actions];
}

// The pages and actions whose name holds every word typed.
export function matchItems(items, text) {
	const words = String(text || "")
		.toLowerCase()
		.split(/\s+/)
		.filter(Boolean);
	if (!words.length) return items;
	return items.filter((item) => words.every((word) => item.label.toLowerCase().includes(word)));
}
