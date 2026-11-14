// The app's search: what each kind of result is called and how it shows, reusing the rows the
// Register, Filings and Legal lists already use.
import { taskRow } from "@/lib/filings";
import { itemRow } from "@/lib/items";
import { caseRow, markRow } from "@/lib/legal";

export const MIN_LENGTH = 2;

export const SECTIONS = [
	{ key: "items", label: "Register", toRow: itemRow },
	{ key: "filings", label: "Filings", toRow: taskRow },
	{ key: "cases", label: "Cases", toRow: caseRow },
	{ key: "trademarks", label: "Trademarks", toRow: markRow },
];

// The sections that found something, each with its rows, in the order above.
export function resultSections(results, today = new Date()) {
	return SECTIONS.map((section) => ({
		...section,
		rows: (results?.[section.key] || []).map((record) => section.toRow(record, today)),
	})).filter((section) => section.rows.length);
}
