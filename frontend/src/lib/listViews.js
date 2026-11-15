// What every list in the app shares beyond its rows: grouping by when, and "Only mine".

const DAY = 24 * 60 * 60 * 1000;
export const SOON_DAYS = 30;

const toDate = (value) => (value ? new Date(`${String(value).slice(0, 10)}T00:00:00`) : null);

// Rows in the order given, under Overdue, Next 30 days, Later, No date and Closed; empty groups
// are left out. A row is overdue when it says so (`due.late`) or its date has passed; a closed
// one (`closed`, such as a cancelled licence) is due nothing whatever its date.
export function groupRows(rows, today = new Date()) {
	const midnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());
	const groups = [
		{ key: "overdue", label: "Overdue", rows: [] },
		{ key: "soon", label: `Next ${SOON_DAYS} days`, rows: [] },
		{ key: "later", label: "Later", rows: [] },
		{ key: "none", label: "No date", rows: [] },
		{ key: "closed", label: "Closed", rows: [] },
	];
	const [overdue, soon, later, none, closed] = groups;
	for (const row of rows) {
		const date = toDate(row.date);
		if (row.closed) closed.rows.push(row);
		else if (row.due?.late || (date && date < midnight)) overdue.rows.push(row);
		else if (!date) none.rows.push(row);
		else if ((date - midnight) / DAY <= SOON_DAYS) soon.rows.push(row);
		else later.rows.push(row);
	}
	return groups.filter((group) => group.rows.length);
}

// The server filter for "Only mine", given the field the list keeps the person in.
export function choiceFilters(choices, { mineField, user }) {
	return choices.mine && mineField && user ? [[mineField, "=", user]] : [];
}

// Rows in the order given, under a heading for each value of `labelOf(row)`, the headings in the
// order they first appear (or in `order`, when given). For lists grouped by what they are rather
// than when they are due, such as the obligation library by law.
export function groupBy(rows, labelOf, order = []) {
	const groups = new Map(order.map((label) => [label, []]));
	for (const row of rows) {
		const label = labelOf(row) || "";
		if (!groups.has(label)) groups.set(label, []);
		groups.get(label).push(row);
	}
	return [...groups]
		.filter(([, grouped]) => grouped.length)
		.map(([label, grouped]) => ({
			key: label || "none",
			label: label || "Other",
			rows: grouped,
		}));
}
