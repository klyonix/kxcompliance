// Filing one return for many companies at once: what each row's next step is, and which dropped
// proof file belongs to which row.
import { formatDate } from "@/lib/format";
import { missingDetails, taskActions } from "@/lib/filings";

export const BULK_STATUSES = ["Open", "In Progress", "Ready for Review"];

export const BULK_FIELDS = [
	"name",
	"company",
	"registration_number",
	"status",
	"responsible",
	"reviewer",
	"filed_on",
	"acknowledgement_number",
	"proof",
	"amount_paid",
	"effective_due_date",
	"modified",
	"is_nil",
	"obligation_template",
	"period_label",
	"period_end",
];

export const choiceLabel = (choice) =>
	`${choice.obligation_template} · ${choice.period_label} · ${
		choice.filings
	} to file · due ${formatDate(choice.due)}`;

// What saving would do with a row: send it for review, mark it filed, or nothing (and why).
export function nextStep(row, rules, person) {
	const actions = taskActions(row, rules, person);
	if (row.status === "Ready for Review") {
		return actions.markFiled
			? { status: "Filed", label: "Mark filed" }
			: { status: null, label: "With the reviewer" };
	}
	if (actions.sendForReview) return { status: "Ready for Review", label: "Send for review" };
	if (actions.markFiled) return { status: "Filed", label: "Mark filed" };
	return { status: null, label: "Not yours to file" };
}

// Letters and digits only, in capitals, so "29abcde1234f1z5" in a file name matches a GSTIN.
const plain = (text) =>
	String(text || "")
		.toUpperCase()
		.replace(/[^A-Z0-9]/g, "");

// The shortest number worth matching on; anything shorter turns up in unrelated file names.
const MIN_KEY = 5;

// Dropped files to rows: a file goes to the one row whose registration (GSTIN, TAN, PAN) or
// acknowledgement number is in its name. A file matching no row or several, or a second file for a
// row, is left over for choosing by hand.
export function matchFiles(files, rows) {
	const matched = {};
	const unmatched = [];
	for (const file of files) {
		const name = plain(file.name);
		const hits = rows.filter((row) =>
			[row.registration_number, row.acknowledgement_number]
				.map(plain)
				.some((key) => key.length >= MIN_KEY && name.includes(key))
		);
		if (hits.length === 1 && !matched[hits[0].name]) matched[hits[0].name] = file;
		else unmatched.push(file);
	}
	return { matched, unmatched };
}

// The values a row sends: its details, with the shared filing date where it has none, and its
// next status. Amounts are sent only when the return involves a payment, and never for a NIL one.
export function rowValues(row, sharedDate, rules) {
	const values = {
		filed_on: row.filed_on || sharedDate || null,
		acknowledgement_number: (row.acknowledgement_number || "").trim() || null,
	};
	if (rules?.allows_nil) values.is_nil = row.is_nil ? 1 : 0;
	if (rules?.requires_payment)
		values.amount_paid = row.is_nil ? 0 : Number(row.amount_paid) || 0;
	return values;
}

// A company's NIL filings in the order they must be saved: each return's periods oldest first for
// each registration (GSTIN, TAN), since GST refuses a period while an earlier one is unfiled.
export function nilOrder(rows) {
	return [...rows].sort(
		(a, b) =>
			a.obligation_template.localeCompare(b.obligation_template) ||
			String(a.registration_number || "").localeCompare(
				String(b.registration_number || "")
			) ||
			String(a.period_end).localeCompare(String(b.period_end))
	);
}

// The periods filed one after another: one return (by its form, so monthly and quarterly GSTR-3B
// are one) for one registration. Once one fails, the later ones of the same series wait.
export const nilSeries = (row, rules) =>
	`${rules?.form || row.obligation_template}|${row.registration_number || ""}`;

export const nilChoiceLabel = (choice) =>
	`${choice.company} · ${choice.filings} NIL to file · oldest due ${formatDate(choice.due)}`;

export function rowMissing(row, sharedDate, rules, proofWaiting) {
	return missingDetails({ ...row, ...rowValues(row, sharedDate, rules) }, rules, {
		proofWaiting,
	});
}

// The save button's words for what is ticked: "Send 3 for review", "Mark 2 filed", or "Save 5".
export function saveLabel(steps) {
	const counts = {};
	for (const status of steps) counts[status] = (counts[status] || 0) + 1;
	const kinds = Object.keys(counts);
	if (!kinds.length) return "Nothing ticked";
	if (kinds.length > 1) return `Save ${steps.length}`;
	return kinds[0] === "Filed" ? `Mark ${steps.length} filed` : `Send ${steps.length} for review`;
}

const companiesText = (count) => (count === 1 ? "1 company" : `${count} companies`);

// Who asking in bulk would reach, and why not the rest.
export function askPlanLine({ to_ask: toAsk, asked_already: askedAlready, no_client: noClient }) {
	const parts = [
		toAsk ? `${companiesText(toAsk)} will be asked` : "Nobody is left to ask",
		askedAlready &&
			`${companiesText(askedAlready)} already ${
				askedAlready === 1 ? "has" : "have"
			} a request open`,
		noClient &&
			`${companiesText(noClient)} ${noClient === 1 ? "is" : "are"} not linked to a client`,
	];
	return `${parts.filter(Boolean).join("; ")}.`;
}
