// Billing a firm's clients: the prices it charges per return, and what is sent to the server.

// How a rate is charged (the server's Rate Card Line units): a return per filing; a service by the
// hour or item as it is done, or every month, quarter or year.
export const RETURN_UNITS = ["Per filing"];
export const SERVICE_UNITS = ["Per hour", "Per item", "Per month", "Per quarter", "Per year"];
export const AS_DONE = ["Per hour", "Per item"];

const rateName = (row) =>
	row.kind === "Return" ? row.obligation_template : String(row.service || "").trim();

// A new rate line, of a return or a service.
export const newRate = (kind = "Return") => ({
	kind,
	obligation_template: "",
	service: "",
	unit: kind === "Return" ? "Per filing" : "Per hour",
	amount: "",
	sac_code: "",
});

// What is wrong with a list of rates (the server checks the same), or null.
export function ratesProblem(rows) {
	const seen = new Set();
	for (const row of rows) {
		const name = rateName(row);
		if (!name) {
			return row.kind === "Return"
				? "Choose a return for each rate, or remove the row."
				: "Name each service, or remove the row.";
		}
		const key = `${row.kind}|${name}`;
		if (seen.has(key)) return `${name} has two rates.`;
		seen.add(key);
		const units = row.kind === "Return" ? RETURN_UNITS : SERVICE_UNITS;
		if (!units.includes(row.unit)) return `Choose how ${name} is charged.`;
		const amount = Number(row.amount);
		if (row.amount === "" || !Number.isFinite(amount) || amount < 0) {
			return `Give ${name} a rate of zero or more.`;
		}
	}
	return null;
}

// The rates as the server takes them: what each prices, how, its rate and SAC code.
export const ratesToSend = (rows) =>
	rows.map((row) => ({
		kind: row.kind,
		obligation_template: row.kind === "Return" ? row.obligation_template : null,
		service: row.kind === "Service" ? String(row.service).trim() : null,
		unit: row.unit,
		amount: Number(row.amount),
		sac_code: String(row.sac_code || "").trim() || null,
	}));

// "₹1,500" or "₹1,305.08" in the site's currency, for amounts the firm bills: paise only when
// there are any.
export const money = (amount, currency = "INR") =>
	Number(amount || 0).toLocaleString(undefined, {
		style: "currency",
		currency,
		minimumFractionDigits: Number.isInteger(Number(amount || 0)) ? 0 : 2,
		maximumFractionDigits: 2,
	});

// What is wrong with the typed lines of a bill (the server checks the same), or null.
export function linesProblem(lines) {
	for (const line of lines) {
		if (!String(line.description || "").trim()) return "Say what each line is for.";
		if (!(Number(line.amount) > 0)) return `Give "${line.description}" an amount above zero.`;
	}
	return null;
}

// A bill's total before GST: the filings ticked, the recurring charges if added, services done
// (hours or items times the rate) and the typed lines.
export function billSubtotal({
	filings = [],
	ticked = [],
	recurring = [],
	withRecurring = false,
	services = [],
	rates = [],
	lines = [],
}) {
	const fees = filings
		.filter((filing) => ticked.includes(filing.name))
		.reduce((sum, filing) => sum + Number(filing.fee || 0), 0);
	const periodic = withRecurring
		? recurring.reduce((sum, charge) => sum + Number(charge.amount || 0), 0)
		: 0;
	const done = services.reduce((sum, row) => {
		const rate = rates.find((option) => option.service === row.service);
		return sum + (rate ? Number(rate.amount) * (Number(row.qty) || 0) : 0);
	}, 0);
	const typed = lines.reduce((sum, line) => sum + (Number(line.amount) || 0), 0);
	return fees + periodic + done + typed;
}

// What is wrong with the services added to a bill, or null.
export function servicesProblem(rows) {
	for (const row of rows) {
		if (!row.service) return "Choose a service for each row, or remove it.";
		if (!(Number(row.qty) > 0)) return `Give how many hours or items of ${row.service}.`;
	}
	return null;
}

// The typed lines as the server takes them.
export const linesToSend = (lines) =>
	lines.map((line) => ({
		description: String(line.description).trim(),
		amount: Number(line.amount),
		government: Boolean(line.government),
	}));

// A bill's state as its badge says it: a draft, sent and waiting, part paid, paid, cancelled.
export function billState(bill) {
	if (bill.docstatus === 0) return { label: "Draft", theme: "gray" };
	if (bill.docstatus === 2) return { label: "Cancelled", theme: "red" };
	if (bill.is_return) return { label: "Credit note", theme: "purple" };
	const due = Number(bill.outstanding_amount || 0);
	if (due <= 0) return { label: "Paid", theme: "green" };
	const total = Number(bill.rounded_total || bill.grand_total || 0);
	if (due < total) return { label: "Part paid", theme: "amber" };
	return {
		label: bill.status === "Overdue" ? "Overdue" : "Unpaid",
		theme: bill.status === "Overdue" ? "red" : "blue",
	};
}

// What is wrong with a payment being recorded (the server checks the same), or null.
export function paymentProblem({ amount, tds, paid_on: paidOn, mode }, due) {
	const paid = Number(amount);
	const deducted = Number(tds) || 0;
	if (!(paid > 0)) return "Give the amount received, above zero.";
	if (deducted < 0) return "TDS is zero or more.";
	if (paid + deducted > Number(due) + 0.005) {
		return `That and the TDS come to more than the ${due} still due.`;
	}
	if (!paidOn) return "Give the date it was received.";
	if (!mode) return "Say how it was paid.";
	return null;
}

// What is wrong with an advance being recorded (the server checks the same), or null.
export function advanceProblem({ client, amount, paid_on: paidOn, mode }) {
	if (!client) return "Choose the client who paid.";
	if (!(Number(amount) > 0)) return "Give the amount received, above zero.";
	if (!paidOn) return "Give the date it was received.";
	if (!mode) return "Say how it was paid.";
	return null;
}

// What is wrong with a credit note being made (the server checks the same), or null. `line` is
// the bill line credited, or null for every line not yet credited.
export function creditProblem({ line, amount, reason }) {
	if (line) {
		const credit = Number(amount);
		if (!(credit > 0)) return "Give the amount to credit, above zero.";
		if (credit > Number(line.creditable) + 0.005) {
			return `A credit on this line is at most its ${line.creditable} before GST.`;
		}
	}
	if (!reason?.trim()) return "Say why it is credited.";
	return null;
}

// The Billing list's tabs (the server's billing.BILL_VIEWS), and what each says when empty.
export const BILL_VIEWS = [
	{
		value: "drafts",
		label: "Drafts",
		empty: { title: "No drafts", detail: "Bills made but not sent yet appear here to check." },
	},
	{
		value: "unpaid",
		label: "Unpaid",
		empty: {
			title: "Nothing unpaid",
			detail: "Sent bills with something still due appear here.",
		},
	},
	{
		value: "paid",
		label: "Paid",
		empty: { title: "Nothing paid yet", detail: "Bills paid in full appear here." },
	},
	{
		value: "all",
		label: "All",
		empty: {
			title: "No bills yet",
			detail: "Make one from a client's page, or with New bill.",
		},
	},
];
