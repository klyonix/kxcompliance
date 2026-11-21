// Rules for showing a Compliance Task and what each person may do with it, kept apart from
// the screens so they can be tested. They mirror the checks the server makes on save.
import { formatDate } from "@/lib/format";
import { relativeDue } from "@/pages/myWork";

export const CLOSED_STATUSES = ["Filed", "Filed Late", "Not Applicable", "Cancelled"];
const FILED_STATUSES = ["Filed", "Filed Late"];
const APPROVER_ROLES = ["Compliance Manager", "System Manager"];

export const FILING_VIEWS = [
	{
		label: "To file",
		value: "open",
		filters: [["status", "in", ["Open", "In Progress"]]],
		orderBy: "effective_due_date asc",
		group: true,
	},
	{
		label: "For review",
		value: "review",
		filters: [["status", "=", "Ready for Review"]],
		orderBy: "effective_due_date asc",
		group: true,
	},
	{
		label: "NIL to file",
		value: "nil",
		filters: [
			["is_nil", "=", 1],
			["status", "in", ["Open", "In Progress", "Ready for Review"]],
		],
		orderBy: "effective_due_date asc",
		group: true,
	},
	{
		label: "Done",
		value: "done",
		filters: [["status", "in", CLOSED_STATUSES]],
		orderBy: "effective_due_date desc",
	},
];

export const TASK_LIST_FIELDS = [
	"name",
	"obligation_template",
	"period_label",
	"company",
	"status",
	"is_overdue",
	"effective_due_date",
	"filed_on",
	"responsible",
	"is_nil",
];

// The filings list's columns, boards and filters (RecordList).
export const FILING_LIST = {
	columns: [
		{ label: "Company", field: "company" },
		{ label: "Responsible", field: "responsible", person: true },
	],
	dateLabel: "Due",
	boards: ["filings-stage"],
	filterBy: { mine: "responsible" },
};

// The filing details the app can change, in the order the form shows them.
export const FILING_FIELDS = [
	"is_nil",
	"filed_on",
	"acknowledgement_number",
	"proof",
	"amount_paid",
	"interest",
	"late_fee",
	"remarks",
];

export function taskTheme(status, overdue) {
	if (overdue) return "red";
	if (status === "Filed") return "green";
	if (["Ready for Review", "Filed Late"].includes(status)) return "amber";
	if (status === "In Progress") return "blue";
	return "gray";
}

function dueFor(task, midnight) {
	if (FILED_STATUSES.includes(task.status) && task.filed_on) {
		return { text: `Filed ${formatDate(task.filed_on, { year: false })}`, late: false };
	}
	if (CLOSED_STATUSES.includes(task.status)) return { text: "", late: false };
	return relativeDue(task.effective_due_date, midnight, { overdue: Boolean(task.is_overdue) });
}

// The obligation library as a searchable choice, grouped by law (a return with none under Other).
export function returnGroups(templates) {
	const byLaw = new Map();
	for (const template of templates) {
		const law = template.law || "Other";
		if (!byLaw.has(law)) byLaw.set(law, []);
		byLaw.get(law).push({
			// The form is added only where the return's name does not already say it.
			label:
				template.form && !template.name.toLowerCase().includes(template.form.toLowerCase())
					? `${template.name} (${template.form})`
					: template.name,
			value: template.name,
		});
	}
	return [...byLaw.entries()]
		.sort(([a], [b]) => a.localeCompare(b))
		.map(([group, options]) => ({ group, options }));
}

export function taskRow(task, today = new Date()) {
	const midnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());
	return {
		key: task.name,
		kind: "filing",
		title: task.obligation_template,
		detail: [task.period_label, task.company, task.is_nil && "NIL"]
			.filter(Boolean)
			.join(" · "),
		status: task.status,
		theme: taskTheme(task.status, Boolean(task.is_overdue)),
		due: dueFor(task, midnight),
		date: task.effective_due_date,
		to: { name: "ComplianceTask", params: { name: task.name } },
	};
}

// A one-person team: the preparer has no one else set to check their filing.
export function checksOwnFiling(task, user) {
	return task.responsible === user && (!task.reviewer || task.reviewer === user);
}

// What a person may do with a task. `rules` is the task's obligation template.
export function taskActions(task, rules, { user, roles }) {
	const none = { edit: false, sendForReview: false, markFiled: false, sendBack: false };
	if (!task || !rules || CLOSED_STATUSES.includes(task.status)) return none;
	const approver = roles.some((role) => APPROVER_ROLES.includes(role));
	if (!approver && ![task.responsible, task.reviewer].includes(user)) return none;
	const inReview = task.status === "Ready for Review";
	// The person who prepared a reviewed filing cannot also mark it filed, unless they are a
	// manager with no one else set to check it (a one-person team), who files it straight away.
	if (rules.requires_review && approver && checksOwnFiling(task, user)) {
		return { edit: true, sendForReview: false, markFiled: true, sendBack: false };
	}
	const mayMarkFiled = rules.requires_review
		? user !== task.responsible && (user === task.reviewer || approver)
		: true;
	return {
		edit: true,
		sendForReview: Boolean(rules.requires_review) && !inReview,
		markFiled: mayMarkFiled,
		sendBack: inReview && mayMarkFiled,
	};
}

// A NIL period of a return that gives no acknowledgement for it (a TDS non-filing declaration on
// TRACES): only the date it was declared is needed. The server makes the same check.
export const nilDeclared = (values, rules) =>
	Boolean(Number(values?.is_nil) && rules?.allows_nil && !rules.nil_needs_acknowledgement);

// Filing details still to fill in before a task can go for review or be marked filed.
export function missingDetails(values, rules, { proofWaiting = false } = {}) {
	const missing = [];
	if (!values.filed_on) missing.push("Filed on");
	if (nilDeclared(values, rules)) return missing;
	if (!(values.acknowledgement_number || "").trim()) missing.push("Acknowledgement number");
	if (rules?.requires_proof && !values.proof && !proofWaiting) missing.push("Proof");
	return missing;
}

const AMOUNT_FIELDS = ["amount_paid", "interest", "late_fee"];
// Ticks, sent as 0 or 1.
const CHECK_FIELDS = ["is_nil"];
// A NIL return pays no tax and no interest; a late fee may still be paid on one filed late.
export const NIL_ZERO_FIELDS = ["amount_paid", "interest"];

// What the form shows for a saved task: amounts of zero stay blank.
export function formValues(task) {
	return Object.fromEntries(
		FILING_FIELDS.map((field) => {
			const value = task[field] ?? "";
			if (CHECK_FIELDS.includes(field)) return [field, Boolean(Number(value))];
			return [field, AMOUNT_FIELDS.includes(field) && !Number(value) ? "" : value];
		})
	);
}

// Only what changed, so a save never sends back values nobody touched.
export function changedValues(values, saved) {
	const changed = {};
	for (const field of FILING_FIELDS) {
		if (field === "proof") continue;
		const now = values[field] ?? "";
		const before = saved[field] ?? "";
		if (CHECK_FIELDS.includes(field)) {
			if (Boolean(Number(now)) !== Boolean(Number(before))) changed[field] = now ? 1 : 0;
		} else if (AMOUNT_FIELDS.includes(field)) {
			if (Number(now) !== Number(before)) changed[field] = Number(now);
		} else if (String(now) !== String(before)) {
			changed[field] = now === "" ? null : now;
		}
	}
	return changed;
}

// The steps a filing goes through, for the line at the top of its page.
export function filingSteps(task, rules) {
	const steps = ["File", ...(rules?.requires_review ? ["Review"] : []), "Filed"];
	let current = 0;
	if (CLOSED_STATUSES.includes(task.status)) current = steps.length - 1;
	else if (task.status === "Ready for Review") current = steps.indexOf("Review");
	return { steps, current: Math.max(current, 0) };
}

// Whether anything about the filing itself has been recorded yet (remarks are notes, not filing).
export const hasFilingDetails = (task) =>
	Boolean(
		task.filed_on ||
			task.acknowledgement_number ||
			task.proof ||
			["amount_paid", "interest", "late_fee"].some((field) => Number(task[field]))
	);

// When the filing fields show: once someone starts recording it, or straight away if something
// is already recorded on an open filing. In review they stay folded unless someone asks to correct.
export function showFilingForm(task, { editable, opened }) {
	if (!editable || CLOSED_STATUSES.includes(task.status)) return false;
	if (task.status === "Ready for Review") return opened;
	return opened || hasFilingDetails(task);
}
