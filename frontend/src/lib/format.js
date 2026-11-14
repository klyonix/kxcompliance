// How the app writes dates. The order follows the site's date format setting (the one the
// Desk uses), so a day-first site reads "13 Nov 2026" and a month-first one "Nov 13, 2026".
import { boot } from "@/boot";

export const dayFirst = () => !String(boot.dateFormat || "dd-mm-yyyy").startsWith("mm");
const locale = () => (dayFirst() ? "en-GB" : "en-US");

export function formatDate(value, { year = true, weekday = false } = {}) {
	if (!value) return "";
	return new Date(`${String(value).slice(0, 10)}T00:00:00`).toLocaleDateString(locale(), {
		weekday: weekday ? "short" : undefined,
		day: "numeric",
		month: "short",
		year: year ? "numeric" : undefined,
	});
}

export function formatDateTime(value) {
	if (!value) return "";
	return new Date(String(value).replace(" ", "T")).toLocaleString(locale(), {
		dateStyle: "medium",
		timeStyle: "short",
	});
}

// The same order for what a date picker shows, in its own (dayjs) tokens.
export const pickerFormat = () => (dayFirst() ? "D MMM YYYY" : "MMM D, YYYY");
