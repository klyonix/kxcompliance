import { boot, checksOnly, isManager } from "./boot";

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
	// CA/CS firms only.
	{ label: "Clients", route: "Clients", icon: "lucide-users", firm: true },
	{ label: "Filings", route: "Filings", icon: "lucide-calendar-check" },
	{ label: "Register", route: "Register", icon: "lucide-file-badge" },
	{ label: "Legal", route: "Legal", icon: "lucide-scale" },
	{
		label: "Licence Check",
		// The phone's tab bar has room for one short word.
		tabLabel: "Licences",
		route: "LicenceCheck",
		icon: "lucide-shield-check",
		// A firm checks licences on its clients' sales only if it turns this on (not built yet).
		organisation: true,
	},
];

export const sections = checksOnly()
	? ALL_SECTIONS.filter((section) => section.route === "LicenceCheck")
	: ALL_SECTIONS.filter((section) => {
			const firm = boot.accountType === "CA/CS Firm";
			if (section.managers && !isManager()) return false;
			if (section.firm && !firm) return false;
			return !(section.organisation && firm);
	  });

// Where each record opens until it has a screen of its own in the app.
export const deskRoute = (doctype, name) =>
	`/app/${doctype.toLowerCase().replace(/ /g, "-")}/${encodeURIComponent(name)}`;

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
