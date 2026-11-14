// Bulk setup: how a checked or imported sheet reads, row by row and in total.

export const OUTCOME_THEMES = {
	Ready: "blue",
	Made: "green",
	Skipped: "gray",
	Error: "red",
	Failed: "red",
};

export const RUNNING_STATUSES = ["Queued", "Importing"];

export function importSummary(rows) {
	const count = (outcomes) => rows.filter((row) => outcomes.includes(row.outcome)).length;
	return {
		ready: count(["Ready"]),
		made: count(["Made"]),
		skipped: count(["Skipped"]),
		problems: count(["Error", "Failed"]),
		total: rows.length,
	};
}

// Problems first, so they are fixed before anything else is looked at; then the sheet's order.
export function sortedRows(rows) {
	const rank = (row) => (["Error", "Failed"].includes(row.outcome) ? 0 : 1);
	return [...rows].sort((a, b) => rank(a) - rank(b) || a.row_number - b.row_number);
}

const counted = (count, one, many) => `${count} ${count === 1 ? one : many}`;

export function summaryLine(summary, status) {
	const parts = [];
	if (status === "Checked") {
		parts.push(`${counted(summary.ready, "company", "companies")} ready to set up`);
		if (summary.skipped) parts.push(`${summary.skipped} already set up`);
		if (summary.problems) parts.push(`${counted(summary.problems, "row", "rows")} to fix`);
	} else {
		parts.push(`${counted(summary.made, "company", "companies")} set up`);
		if (summary.ready) parts.push(`${summary.ready} to go`);
		if (summary.problems) parts.push(`${counted(summary.problems, "row", "rows")} not set up`);
	}
	return parts.join(" · ");
}
