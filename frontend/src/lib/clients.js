// How a firm's clients show: what needs attention, in words and colour.

export function clientAttention(client) {
	const parts = [];
	if (client.overdue) parts.push(`${client.overdue} overdue`);
	if (client.due_this_week) parts.push(`${client.due_this_week} due this week`);
	if (client.in_review) parts.push(`${client.in_review} waiting for review`);
	return parts.length ? parts.join(" · ") : "Nothing due this week";
}

export function clientTheme(client) {
	if (client.overdue) return "red";
	if (client.due_this_week || client.in_review) return "amber";
	return "green";
}

export function companiesLine(companies) {
	if (!companies.length) return "No companies yet";
	if (companies.length === 1) return companies[0];
	return `${companies[0]} and ${companies.length - 1} more`;
}

const money = (amount, currency) =>
	new Intl.NumberFormat(undefined, {
		style: currency ? "currency" : "decimal",
		currency: currency || undefined,
		maximumFractionDigits: 0,
	}).format(amount || 0);

// A client's year in a few numbers, each with a tone: red or amber when it needs the firm.
export function yearFacts(year, { client = false } = {}) {
	const counted = year.on_time + year.late + year.overdue;
	const paid = (year.late_fee || 0) + (year.interest || 0);
	return [
		{
			label: "Filed on time",
			value: counted ? `${Math.round((year.on_time * 100) / counted)}%` : "—",
			detail: counted ? `${year.on_time} of ${counted} filings` : "No filings due yet",
			tone: !counted || year.on_time === counted ? "gray" : year.overdue ? "red" : "amber",
		},
		{
			label: "Overdue",
			value: String(year.overdue),
			detail: `${year.late} filed late`,
			tone: year.overdue ? "red" : "gray",
		},
		{
			label: "Late fees and interest",
			value: money(paid, year.currency),
			detail: paid ? "Paid on late filings" : "None paid",
			tone: paid ? "amber" : "gray",
		},
		{
			label: "Open notices and cases",
			value: String(year.open_cases),
			detail: "Open now",
			tone: year.open_cases ? "amber" : "gray",
		},
		{
			label: client ? "Documents your firm needs" : "Documents awaited",
			value: String(year.waiting_on_client),
			detail: client ? "Waiting for you" : "From the client",
			tone: year.waiting_on_client ? "amber" : "gray",
		},
		{
			label: "DSCs expiring",
			value: String(year.dscs_expiring),
			detail: "Expired or within 30 days",
			tone: year.dscs_expiring ? "red" : "gray",
		},
	];
}
