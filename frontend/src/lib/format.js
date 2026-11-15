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

// What a date field shows and reads when typed: the site's own date format (dd-mm-yyyy and the
// like) in dayjs tokens. The picker reads typed text only in the shape it shows, so a format
// with month names would refuse 10-12-2026.
export function pickerFormat() {
	const own = (boot.dateFormat || "").trim();
	return /^[dmy]+([-/.])[dmy]+\1[dmy]+$/i.test(own) ? own.toUpperCase() : "DD-MM-YYYY";
}

// An amount of money, whole units; the app's penalties and fees are in rupees unless told otherwise.
export function formatMoney(amount, currency = "INR") {
	return new Intl.NumberFormat(locale(), {
		style: currency ? "currency" : "decimal",
		currency: currency || undefined,
		maximumFractionDigits: 0,
	}).format(amount || 0);
}
