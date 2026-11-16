import { boot, checksOnly, isClientLogin, isManager, licenceCheckOn, mayUseDesk } from "./boot";

// The app's sections, in the order they appear in the side bar and the phone's tab bar.
const ALL_SECTIONS = [
	// On phones search opens from a button in each page's header, as the tab bar is full.
	{ label: "Search", route: "Search", icon: "lucide-search", desktopOnly: true },
	{ label: "My Work", route: "MyWork", icon: "lucide-inbox", count: "overdue" },
	// Managers only; on phones it opens from My Work, as the tab bar has no room for it.
	{
		label: "Overview",
		route: "Overview",
		icon: "lucide-layout-dashboard",
		managers: true,
		desktopOnly: true,
	},
	// A client's own login lands here: their companies and open filings.
	{ label: "Home", route: "ClientHome", icon: "lucide-house", clientLogin: true },
	// CA/CS firms only.
	{ label: "Clients", route: "Clients", icon: "lucide-users", firm: true },
	// A firm's bills to its clients, for those who may bill: under Clients in the side bar
	// (sectionsFor); on phones it opens from a client's page.
	{
		label: "Client billing",
		route: "Billing",
		icon: "lucide-receipt",
		billing: true,
		desktopOnly: true,
	},
	{ label: "Filings", route: "Filings", icon: "lucide-calendar-check" },
	// On phones it opens from My Work, as the tab bar is full.
	{ label: "Calendar", route: "MonthCalendar", icon: "lucide-calendar-days", desktopOnly: true },
	{ label: "Register", route: "Register", icon: "lucide-file-badge" },
	{ label: "Legal", route: "Legal", icon: "lucide-scale" },
	{
		label: "Licence Check",
		// The phone's tab bar has room for one short word.
		tabLabel: "Licences",
		route: "LicenceCheck",
		icon: "lucide-shield-check",
		// On a firm's site, once a client is switched on for it.
		licenceCheck: true,
	},
	// Managers only; on phones it opens from Account, as the tab bar is full.
	{
		label: "Settings",
		route: "Settings",
		icon: "lucide-settings",
		// What the tours point at in the side bar (data-tour).
		tour: "settings-nav",
		managers: true,
		desktopOnly: true,
	},
	// On phones it opens from Account, as the tab bar is full.
	{ label: "Reports", route: "Reports", icon: "lucide-file-chart-column", desktopOnly: true },
	// The user manual; on phones it opens from the question mark on every page.
	{ label: "Help", route: "Help", icon: "lucide-book-open", desktopOnly: true },
];

// What a client's login may open: their home, the records of their companies, and search.
export const CLIENT_ROUTES = [
	"ClientHome",
	"DocumentRequest",
	"Search",
	"Filings",
	"ComplianceTask",
	"Register",
	"ComplianceItem",
	"Signatories",
	"Signatory",
	"Legal",
	"LegalCase",
	"Trademark",
	"Account",
	"Help",
	"PrivacyNotice",
];
const CLIENT_SECTIONS = ["Search", "ClientHome", "Filings", "Register", "Legal", "Help"];

export function sectionsFor({ checks, client }) {
	if (checks) return ALL_SECTIONS.filter((section) => section.route === "LicenceCheck");
	if (client) return ALL_SECTIONS.filter((section) => CLIENT_SECTIONS.includes(section.route));
	const firm = boot.accountType === "CA/CS Firm";
	// A firm's manager finds Billing before it is set up; it opens the setup.
	const setUpBilling = firm && isManager() && !boot.billingSetUp;
	const shown = ALL_SECTIONS.filter((section) => {
		if (section.managers && !isManager()) return false;
		if (section.firm && !firm) return false;
		if (section.clientLogin) return false;
		if (section.billing && !boot.mayBill && !setUpBilling) return false;
		return !(section.licenceCheck && !licenceCheckOn());
	}).map((section) =>
		section.billing && !boot.mayBill ? { ...section, route: "BillingSettings" } : section
	);
	return withClientBilling(shown);
}

// What opens from Clients and from Client billing, so each row stays marked on those pages.
const CLIENT_PAGES = ["ClientNew", "ClientEdit", "BulkSetup", "Client", "DocumentRequest"];
const BILLING_PAGES = ["NewBill", "Payment", "Bill"];

// Client billing sits under Clients (RK, 17 Nov 2026): Clients becomes a group of the two.
function withClientBilling(shown) {
	const billing = shown.find((section) => section.billing);
	const clients = shown.find((section) => section.route === "Clients");
	if (!billing || !clients) return shown;
	const group = {
		...clients,
		pages: [
			{ label: "Clients", route: "Clients", also: CLIENT_PAGES },
			{
				label: billing.label,
				route: billing.route,
				also: BILLING_PAGES,
				// Before billing is set up the row opens Billing setup, whose own row is marked there.
				marksOwnRoute: billing.route === "Billing",
			},
		],
	};
	return shown
		.filter((section) => section !== billing)
		.map((section) => (section === clients ? group : section));
}

export const sections = sectionsFor({ checks: checksOnly(), client: isClientLogin() });

// A page another app adds (plugins.js): in the side bar before Settings, or in the Settings group.
export function addMenuPage(place, page) {
	if (place === "settings") {
		SETTINGS_PAGES.push(page);
		return;
	}
	const settings = sections.findIndex((section) => section.route === "Settings");
	sections.splice(settings === -1 ? sections.length : settings, 0, {
		desktopOnly: true,
		...page,
	});
}

// The pages under Settings: a group in the side bar, and buttons on the Settings page on phones.
// `also` lists the routes opened from a page, so its row stays marked while one is open.
const SETTINGS_PAGES = [
	{ label: "General", route: "Settings", icon: "lucide-sliders-horizontal" },
	{ label: "People", route: "People", icon: "lucide-users", also: ["Person"] },
	{
		label: "Companies",
		route: "Companies",
		icon: "lucide-building-2",
		also: ["Company", "CompanyNew"],
	},
	{
		label: "Register item types",
		route: "ItemTypes",
		icon: "lucide-file-badge",
		also: ["ItemTypeNew", "ItemType"],
	},
	{
		label: "Customer and supplier licences",
		route: "LicenceRules",
		icon: "lucide-shield-check",
		also: ["LicenceRuleNew", "LicenceRule", "LicenceBlocks"],
		licenceCheck: true,
	},
	{ label: "Billing setup", route: "BillingSettings", icon: "lucide-receipt", firm: true },
	{ label: "Reminder log", route: "ReminderLog", icon: "lucide-bell" },
	{
		label: "Obligation library",
		route: "ObligationLibrary",
		icon: "lucide-library",
		also: ["ObligationNew", "Obligation"],
	},
	{
		label: "Due-date extensions",
		route: "Extensions",
		icon: "lucide-calendar-clock",
		also: ["ExtensionNew", "Extension"],
	},
	{
		label: "Privacy requests",
		route: "PrivacyRequests",
		icon: "lucide-user-lock",
		also: ["PrivacyRequest"],
	},
	{
		label: "Data breaches",
		route: "Breaches",
		icon: "lucide-shield-alert",
		also: ["BreachNew", "Breach"],
	},
];

export const settingsPagesFor = ({
	licenceCheck = licenceCheckOn(),
	firm = boot.accountType === "CA/CS Firm",
} = {}) =>
	SETTINGS_PAGES.filter(
		(page) => !(page.licenceCheck && !licenceCheck) && !(page.firm && !firm)
	);

// Whether a settings page's row is the one open, counting the pages opened from it.
export const isSettingsPageOpen = (page, routeName) =>
	(page.route === routeName && page.marksOwnRoute !== false) ||
	(page.also || []).includes(routeName);

// Back to where the person came from in the app, with that list's tab and search as they left
// them; to the record's list when the page was opened directly (a link, a reload).
export function goBack(router, fallback) {
	if (window.history.state?.back) router.back();
	else router.push(fallback);
}

// The Desk's address in Frappe 16 (/app still redirects there, one step slower).
export const DESK = "/desk";
export const deskPath = (path = "") => `${DESK}${path ? `/${path}` : ""}`;

// Where each record opens until it has a screen of its own in the app.
export const deskRoute = (doctype, name) =>
	deskPath(`${doctype.toLowerCase().replace(/ /g, "-")}/${encodeURIComponent(name)}`);

// A record menu's "Open in the Desk", for those who have the Desk.
export const deskActions = (doctype, name) =>
	mayUseDesk()
		? [
				{
					label: "Open in the Desk",
					icon: "lucide-app-window",
					onClick: () => (window.location.href = deskRoute(doctype, name)),
				},
		  ]
		: [];

export async function signOut({ unsent, clear }) {
	if (
		unsent &&
		!window.confirm(
			`${unsent} change(s) made on this device have not reached the server and will be lost. Sign out anyway?`
		)
	) {
		return;
	}
	await clear();
	await fetch("/api/method/logout", {
		method: "POST",
		headers: { "X-Frappe-CSRF-Token": window.csrf_token || "" },
	});
	window.location.href = "/login?redirect-to=/compliance";
}

// Where someone is sent first on a site, or null to go where they meant to: the privacy notice
// before anything, the setup wizard next on a new site, and never back to the wizard once set up.
// The notice is left alone while setup is due, or each would send to the other for ever (a new
// site's first sign-in has both due).
export function firstRunRoute(to, { privacyNoticeDue, setupNeeded }) {
	if (privacyNoticeDue) {
		return to.name === "PrivacyNotice"
			? null
			: { name: "PrivacyNotice", query: { next: to.fullPath } };
	}
	if (setupNeeded && to.name !== "Onboarding") return { name: "Onboarding" };
	if (!setupNeeded && to.name === "Onboarding") return { name: "MyWork" };
	return null;
}
