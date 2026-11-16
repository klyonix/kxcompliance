import { describe, expect, it, vi } from "vitest";

// frappe-ui and the app's header need a browser build; the plug-in host only passes them on.
vi.mock("frappe-ui", () =>
	Object.fromEntries(
		["Avatar", "Badge", "Button", "Dialog", "Dropdown", "ErrorMessage", "FormControl"]
			.concat(["LoadingIndicator", "Skeleton", "TabButtons", "TextInput", "toast"])
			.concat(["Tabs", "TabList", "TabTrigger", "TabPanel"])
			.map((name) => [name, { name }])
	)
);
vi.mock("@/components/AppPageHeader.vue", () => ({ default: { name: "AppPageHeader" } }));
vi.mock("@/composables/useIsMobile", () => ({ useIsMobile: () => false }));
vi.mock("@/composables/useTabQuery", () => ({ useTabQuery: () => null }));
import { boot, mayUseDesk } from "./boot";
import { sections, settingsPagesFor } from "./navigation";
import { addPage, host, loadPlugins } from "./plugins";

const fakeRouter = () => ({ addRoute: vi.fn() });
const Page = { render: () => null };

describe("plug-in pages", () => {
	it("adds a route and a side bar row before Settings", () => {
		const router = fakeRouter();
		addPage(router, {
			path: "/plan",
			name: "PluginPlan",
			component: Page,
			menu: { label: "Plan", icon: "lucide-credit-card" },
		});
		expect(router.addRoute).toHaveBeenCalledWith({
			path: "/plan",
			name: "PluginPlan",
			component: Page,
		});
		const routes = sections.map((section) => section.route);
		const at = routes.indexOf("PluginPlan");
		expect(at).toBeGreaterThan(-1);
		if (routes.includes("Settings")) expect(at).toBeLessThan(routes.indexOf("Settings"));
		expect(sections[at].desktopOnly).toBe(true);
	});

	it("adds a page to the Settings group, marked on the pages opened from it", () => {
		addPage(fakeRouter(), {
			path: "/settings/billing-plan",
			name: "PluginSettingsPage",
			component: Page,
			also: ["PluginSubPage"],
			menu: { place: "settings", label: "Plan and billing", icon: "lucide-credit-card" },
		});
		const page = settingsPagesFor().find((row) => row.route === "PluginSettingsPage");
		expect(page).toMatchObject({ label: "Plan and billing", also: ["PluginSubPage"] });
	});

	it("refuses a page without a path, name or component", () => {
		expect(() => addPage(fakeRouter(), { path: "/x", name: "X" })).toThrow();
	});

	it("gives plug-ins the app's own pieces", () => {
		const router = fakeRouter();
		const given = host(router);
		expect(given.version).toBe(1);
		expect(given.components.AppPageHeader).toBeTruthy();
		expect(given.ui.Button).toBeTruthy();
		expect(given.ui.Tabs).toBeTruthy();
		expect(given.useIsMobile).toBeTypeOf("function");
		expect(given.useTabQuery).toBeTypeOf("function");
		expect(given.vue.ref).toBeTypeOf("function");
		given.addPage({ path: "/y", name: "Y", component: Page });
		expect(router.addRoute).toHaveBeenCalled();
	});

	it("does nothing when no app adds a plug-in", async () => {
		delete window.kxcompliance;
		await loadPlugins(fakeRouter(), []);
		expect(window.kxcompliance).toBeUndefined();
	});
});

describe("the Desk link", () => {
	it("is hidden when another app keeps the person off the Desk", () => {
		boot.roles = ["Compliance Manager"];
		boot.hideDesk = false;
		expect(mayUseDesk()).toBe(true);
		boot.hideDesk = true;
		expect(mayUseDesk()).toBe(false);
		boot.hideDesk = false;
	});
});
