// The Kanban boards: which field makes the columns, the columns in order, and whether a card may
// be moved. A move saves the field, so the server checks it as it checks the record's own page;
// moves that need more than the field (filing details, proof) open the record instead.
import { call } from "@/api";
import { personOptions } from "@/lib/people";

const OTHER = "__other__";
const RECENT_FILED_DAYS = 30;
const RECENT_CLOSED_DAYS = 90;

const daysAgo = (days, today) => {
	const date = new Date(today.getFullYear(), today.getMonth(), today.getDate() - days);
	const pad = (value) => String(value).padStart(2, "0");
	return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
};

export const BOARDS = {
	"register-status": {
		label: "By status",
		field: "status",
		// The status follows the dates and the renewal, so it is not dragged.
		movable: false,
		// A board shows every item that is not cancelled, whichever tab it was opened from.
		scope: () => ({ filters: [["is_cancelled", "=", 0]] }),
		columns: [
			{ value: "Expired", label: "Expired", hue: "red" },
			{ value: "Lapsed", label: "Lapsed", hue: "red" },
			{ value: "Due for Renewal", label: "Due for renewal", hue: "amber" },
			{ value: "Renewal Planned", label: "Renewal planned", hue: "blue" },
			{ value: "Renewal in Progress", label: "Renewal in progress", hue: "blue" },
			{ value: "Active", label: "Active", hue: "green" },
		],
	},
	"register-responsible": {
		label: "By responsible person",
		field: "responsible",
		movable: true,
		scope: () => ({ filters: [["is_cancelled", "=", 0]] }),
		loadColumns: async () =>
			personOptions(await call("kxcompliance.api.people_options")).map((person) => ({
				value: person.value,
				label: person.label,
				hue: "gray",
			})),
	},
	"filings-stage": {
		label: "By stage",
		field: "status",
		movable: true,
		// Ready for review and filed need the filing's details first, on its page.
		openFor: ["Ready for Review", "Filed", "Filed Late"],
		// Every open filing, and those filed lately.
		scope: (today) => ({
			filters: [["status", "in", ["Open", "In Progress", "Ready for Review"]]],
			also: [
				["status", "in", ["Filed", "Filed Late"]],
				["filed_on", ">=", daysAgo(RECENT_FILED_DAYS, today)],
			],
		}),
		columns: [
			{ value: "Open", label: "To do", hue: "gray" },
			{ value: "In Progress", label: "In progress", hue: "blue" },
			{ value: "Ready for Review", label: "Ready for review", hue: "amber" },
			{ value: "Filed", label: "Filed", hue: "green" },
			{ value: "Filed Late", label: "Filed late", hue: "amber" },
		],
	},
	"cases-status": {
		label: "By status",
		field: "status",
		movable: true,
		// Every open case, and those closed lately.
		scope: (today) => ({
			filters: [["status", "in", ["Open", "Stayed", "Reserved for Order"]]],
			also: [
				["status", "not in", ["Open", "Stayed", "Reserved for Order"]],
				["closed_on", ">=", daysAgo(RECENT_CLOSED_DAYS, today)],
			],
		}),
		columns: [
			{ value: "Open", label: "Open", hue: "blue" },
			{ value: "Stayed", label: "Stayed", hue: "amber" },
			{ value: "Reserved for Order", label: "Reserved for order", hue: "violet" },
			{ value: "Disposed - In Our Favour", label: "Won", hue: "green" },
			{ value: "Disposed - Against Us", label: "Lost", hue: "red" },
			{ value: "Settled", label: "Settled", hue: "teal" },
			{ value: "Withdrawn", label: "Withdrawn", hue: "gray" },
		],
	},
};

export async function boardColumns(board) {
	return board.loadColumns ? board.loadColumns() : board.columns;
}

// The cards under each column, in the order given; cards whose value has no column of their own
// go under "Other", which is shown only when it has any.
export function groupCards(cards, columns, field) {
	const known = new Set(columns.map((column) => column.value));
	const lanes = columns.map((column) => ({ ...column, cards: [] }));
	const other = { value: OTHER, label: "Other", hue: "gray", cards: [], other: true };
	const byValue = Object.fromEntries(lanes.map((lane) => [lane.value, lane]));
	for (const card of cards) {
		const value = card.record[field];
		if (known.has(value)) byValue[value].cards.push(card);
		else other.cards.push(card);
	}
	return other.cards.length ? [...lanes, other] : lanes;
}

// What moving a card does: nothing (same column or a fixed board), open the record, or save.
export function moveAction(board, from, to) {
	if (!board.movable || from === to || to === OTHER) return "none";
	if ((board.openFor || []).includes(to)) return "open";
	return "save";
}
