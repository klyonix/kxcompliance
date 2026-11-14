// Narrowing the app's lists to one client: by the companies the client owns.

// A company that cannot exist, so a client with no companies yet narrows a list to nothing.
const NO_COMPANY = "\u0000";

export function companiesOf(clients, chosen) {
	if (!chosen) return null;
	const client = clients.find((row) => row.name === chosen);
	return client ? client.companies : null;
}

// Filters for a list's query; a view names the field that holds its company.
export function companyFilters(companies, field = "company") {
	if (!companies) return [];
	return [[field, "in", companies.length ? companies : [NO_COMPANY]]];
}

// My Work, kept to the chosen client's companies.
export function keepClientWork(data, companies) {
	if (!data || !companies) return data;
	const ours = (row) => companies.includes(row.company);
	return {
		...data,
		items: data.items.filter(ours),
		tasks: data.tasks.filter(ours),
		legal_dates: data.legal_dates.filter(ours),
	};
}
