// Front-end plug-ins: another app on the site adds pages to this one (its kxcompliance_boot hook
// lists them in boot.plugins). A plug-in is a script that runs before the app starts and calls
// window.kxcompliance.addPage(); it builds its pages with the components given here, so they look
// and behave like the app's own. Without plug-ins nothing changes.
import * as vue from "vue";
import {
	Avatar,
	Badge,
	Button,
	Dialog,
	Dropdown,
	ErrorMessage,
	FormControl,
	LoadingIndicator,
	Skeleton,
	TabButtons,
	TextInput,
	toast,
} from "frappe-ui";
import { ApiError, call } from "@/api";
import { boot, isManager } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { t } from "@/lib/i18n";
import { addMenuPage } from "@/navigation";

// Raised when what is given to plug-ins changes in a way that breaks them.
export const HOST_VERSION = 1;

// Adds a page: its route, and optionally a row in the side bar ({ place: "main" | "settings",
// label, icon }). `also` names routes opened from it, so its row stays marked on them.
export function addPage(router, { path, name, component, menu, also = [] }) {
	if (!path || !name || !component)
		throw new Error("A plug-in page needs a path, name and component.");
	router.addRoute({ path, name, component });
	if (menu) {
		const { place = "main", ...row } = menu;
		addMenuPage(place, { ...row, route: name, also });
	}
}

export function host(router) {
	return {
		version: HOST_VERSION,
		vue,
		ui: {
			Avatar,
			Badge,
			Button,
			Dialog,
			Dropdown,
			ErrorMessage,
			FormControl,
			LoadingIndicator,
			Skeleton,
			TabButtons,
			TextInput,
			toast,
		},
		components: { AppPageHeader },
		ApiError,
		call,
		boot,
		isManager,
		t,
		router,
		addPage: (page) => addPage(router, page),
	};
}

function loadScript(src) {
	return new Promise((resolve) => {
		const script = document.createElement("script");
		script.src = src;
		script.onload = resolve;
		// A plug-in that does not load (offline, removed) leaves the app as it is.
		script.onerror = () => {
			console.warn(`A plug-in did not load: ${src}`);
			resolve();
		};
		document.head.append(script);
	});
}

// Loads each plug-in's style and script, one after another, before the router starts.
export async function loadPlugins(router, plugins = boot.plugins) {
	if (!plugins.length) return;
	window.kxcompliance = host(router);
	for (const { script, style } of plugins) {
		if (style) {
			const link = document.createElement("link");
			link.rel = "stylesheet";
			link.href = style;
			document.head.append(link);
		}
		// An error inside a plug-in is reported by the browser; the app still starts.
		if (script) await loadScript(script);
	}
}
