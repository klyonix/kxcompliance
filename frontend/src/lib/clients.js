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
