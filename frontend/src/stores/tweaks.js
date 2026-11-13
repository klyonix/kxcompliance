// Design variations to compare, shown only when the address has ?tweaks. Kept per browser.
import { reactive, watch } from "vue";

const KEY = "compliance-plus-tweaks";
const saved = (() => {
	try {
		return JSON.parse(localStorage.getItem(KEY) || "{}");
	} catch {
		return {};
	}
})();

export const tweaks = reactive({ density: "relaxed", grouping: "date", ...saved });
export const tweaksEnabled = new URLSearchParams(window.location.search).has("tweaks");

watch(tweaks, (value) => {
	try {
		localStorage.setItem(KEY, JSON.stringify(value));
	} catch {
		// Private browsing: the choice lasts for this visit only.
	}
});
