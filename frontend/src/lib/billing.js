// Billing a firm's clients: the prices it charges per return, and what is sent to the server.

// What is wrong with a list of prices (the server checks the same), or null.
export function pricesProblem(rows) {
	const seen = new Set();
	for (const row of rows) {
		if (!row.obligation_template) return "Choose a return for each price, or remove the row.";
		if (seen.has(row.obligation_template)) return `${row.obligation_template} has two prices.`;
		seen.add(row.obligation_template);
		const amount = Number(row.amount);
		if (row.amount === "" || !Number.isFinite(amount) || amount < 0) {
			return `Give ${row.obligation_template} a fee of zero or more.`;
		}
	}
	return null;
}

// The prices as the server takes them: a return and its fee, nothing else.
export const pricesToSend = (rows) =>
	rows.map((row) => ({
		obligation_template: row.obligation_template,
		amount: Number(row.amount),
	}));

// "₹1,500" in the site's currency, for amounts the firm bills.
export const money = (amount, currency = "INR") =>
	Number(amount || 0).toLocaleString(undefined, {
		style: "currency",
		currency,
		maximumFractionDigits: 0,
	});

// What is wrong with the typed lines of a bill (the server checks the same), or null.
export function linesProblem(lines) {
	for (const line of lines) {
		if (!String(line.description || "").trim()) return "Say what each line is for.";
		if (!(Number(line.amount) > 0)) return `Give "${line.description}" an amount above zero.`;
	}
	return null;
}

// A bill's total before GST: the filings ticked, the fixed fee if added, and the typed lines.
export function billSubtotal({
	filings = [],
	ticked = [],
	fixedFee = 0,
	withFee = false,
	lines = [],
}) {
	const fees = filings
		.filter((filing) => ticked.includes(filing.name))
		.reduce((sum, filing) => sum + Number(filing.fee || 0), 0);
	const typed = lines.reduce((sum, line) => sum + (Number(line.amount) || 0), 0);
	return fees + (withFee ? Number(fixedFee || 0) : 0) + typed;
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
