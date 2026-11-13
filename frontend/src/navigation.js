// The app's sections, in the order they appear in the side bar and the phone's tab bar.
export const sections = [
	{ label: "My Work", route: "MyWork", icon: "lucide-inbox", count: "overdue" },
	{ label: "Register", route: "Register", icon: "lucide-file-badge" },
];

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
