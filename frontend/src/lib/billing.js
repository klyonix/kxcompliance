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
