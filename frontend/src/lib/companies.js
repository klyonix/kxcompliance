// The companies list: those set up for compliance, then ERPNext companies not set up yet.

const none = { text: "", late: false };

// `overview` is what kxcompliance.api.companies_overview returns.
export function companyGroups(overview) {
	const setUp = overview.companies.map((company) => ({
		key: company.company,
		kind: "company",
		title: company.company,
		detail: [company.company_type, company.client_name || company.client]
			.filter(Boolean)
			.join(" · "),
		status: "Set up",
		theme: "green",
		due: none,
		cells: [String(company.registrations), String(company.obligations)],
		to: { name: "Company", params: { company: company.company } },
	}));
	const notSetUp = overview.not_set_up.map((company) => ({
		key: company,
		kind: "company",
		title: company,
		detail: "In ERPNext. Open it to set it up for compliance.",
		status: "Not set up",
		theme: "gray",
		due: none,
		cells: ["", ""],
		to: { name: "CompanyNew", query: { company } },
	}));
	return [
		{ key: "set-up", label: "Set up for compliance", rows: setUp },
		{ key: "not-set-up", label: "In ERPNext, not set up yet", rows: notSetUp },
	].filter((group) => group.rows.length);
}

// What a filter keeps of the companies overview: those of the client chosen (then only companies
// set up, as only they have a client), whose name has the text, set up or not ("" either).
export function filterCompanies(overview, { client = "", text = "", show = "" } = {}) {
	const words = text.trim().toLowerCase();
	const named = (name) => !words || name.toLowerCase().includes(words);
	return {
		companies:
			show === "not-set-up"
				? []
				: overview.companies.filter(
						(company) =>
							(!client || company.client === client) && named(company.company)
				  ),
		not_set_up:
			show === "set-up" || client ? [] : overview.not_set_up.filter((name) => named(name)),
	};
}
