// How a firm's clients show: what needs attention, in words and colour.
import { formatMoney } from "@/lib/format";
import { t } from "@/lib/i18n";

export function clientAttention(client) {
	const parts = [];
	if (client.overdue) parts.push(t("{0} overdue", client.overdue));
	if (client.due_this_week) parts.push(t("{0} due this week", client.due_this_week));
	if (client.in_review) parts.push(t("{0} waiting for review", client.in_review));
	return parts.length ? parts.join(" · ") : t("Nothing due this week");
}

export function clientTheme(client) {
	if (client.overdue) return "red";
	if (client.due_this_week || client.in_review) return "amber";
	return "green";
}

// How a client shows in the clients list (RowList).
export function clientRow(client) {
	const theme = clientTheme(client);
	const score = client.lowest_score;
	return {
		key: client.name,
		kind: "client",
		title: client.name,
		detail: companiesLine(client.companies),
		status: { red: "Overdue", amber: "Due soon", green: "On track" }[theme],
		theme,
		due: { text: "", late: false },
		cells: [score ? `${score.score} · ${score.company}` : "", clientAttention(client)],
		to: { name: "Client", params: { name: client.name } },
	};
}

export function companiesLine(companies) {
	if (!companies.length) return "No companies yet";
	if (companies.length === 1) return companies[0];
	return `${companies[0]} and ${companies.length - 1} more`;
}

// A client's year in a few numbers, each with a tone: red or amber when it needs the firm.
export function yearFacts(year, { client = false } = {}) {
	const counted = year.on_time + year.late + year.overdue;
	const paid = (year.late_fee || 0) + (year.interest || 0);
	return [
		{
			label: t("Filed on time"),
			value: counted ? `${Math.round((year.on_time * 100) / counted)}%` : "—",
			detail: counted
				? t("{0} of {1} filings", year.on_time, counted)
				: t("No filings due yet"),
			tone: !counted || year.on_time === counted ? "gray" : year.overdue ? "red" : "amber",
		},
		{
			label: t("Overdue"),
			value: String(year.overdue),
			detail: t("{0} filed late", year.late),
			tone: year.overdue ? "red" : "gray",
		},
		{
			label: t("Late fees and interest"),
			value: formatMoney(paid, year.currency),
			detail: paid ? t("Paid on late filings") : t("None paid"),
			tone: paid ? "amber" : "gray",
		},
		{
			label: t("Open notices and cases"),
			value: String(year.open_cases),
			detail: t("Open now"),
			tone: year.open_cases ? "amber" : "gray",
		},
		{
			label: client ? t("Documents your firm needs") : t("Documents awaited"),
			value: String(year.waiting_on_client),
			detail: client ? t("Waiting for you") : t("From the client"),
			tone: year.waiting_on_client ? "amber" : "gray",
		},
		{
			label: t("DSCs expiring"),
			value: String(year.dscs_expiring),
			detail: t("Expired or within 30 days"),
			tone: year.dscs_expiring ? "red" : "gray",
		},
	];
}
