// What every list in the app shares beyond its rows: grouping by when, the filters and the sort a
// person chose (kept in the address), and reading those back from an address anyone can edit.

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

// The filters and sort in the address, kept only when the list offers them: a company the person
// may pick, a type from the list's choices, "mine", and one of the list's sorts.
export function readListChoices(query, { sorts = [], companies = [], types = null } = {}) {
	const choices = {};
	if (typeof query.sort === "string" && sorts.some((sort) => sort.value === query.sort)) {
		choices.sort = query.sort;
	}
	if (typeof query.company === "string" && companies.includes(query.company)) {
		choices.company = query.company;
	}
	if (typeof query.type === "string" && query.type && (!types || types.includes(query.type))) {
		choices.type = query.type;
	}
	if (query.mine === "1") choices.mine = true;
	return choices;
}

// The server filters for the choices, given the fields the list filters on.
export function choiceFilters(choices, { companyField = "company", typeField, mineField, user }) {
	const filters = [];
	if (choices.company) filters.push([companyField, "=", choices.company]);
	if (choices.type && typeField) filters.push([typeField, "=", choices.type]);
	if (choices.mine && mineField && user) filters.push([mineField, "=", user]);
	return filters;
}

// The order to load in: the chosen sort, else the view's own.
export function orderFor(choices, sorts, viewOrder) {
	return sorts.find((sort) => sort.value === choices.sort)?.orderBy || viewOrder;
}

export const choiceCount = (choices) =>
	["company", "type", "mine"].filter((key) => choices[key]).length;
