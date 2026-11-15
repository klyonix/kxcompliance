// Onboarding: the steps for each kind of site, and the answers as the server takes them.

export const ACCOUNT_CHOICES = [
	{
		value: "Organisation",
		label: "An organisation",
		detail: "Your own company, or a group of related companies, keeping its compliance in order.",
		icon: "lucide-building-2",
	},
	{
		value: "CA/CS Firm",
		label: "A CA or CS firm",
		detail: "You look after compliance for clients, each with one or more companies.",
		icon: "lucide-briefcase",
	},
];

export const NUMBER_HINTS = {
	GST: "29ABCDE1234F1Z5",
	"GST Composition": "29ABCDE1234F1Z5",
	TAN: "BLRA12345B",
	PF: "KN/BNG/0012345",
	ESI: "53000123450001001",
	IEC: "ABCDE1234F",
	FSSAI: "11226999000123",
	"Stock Exchange": "NSE: SYMBOL",
};

export function onboardingSteps(accountType) {
	const firm = accountType === "CA/CS Firm" ? ["firm"] : [];
	return ["who", ...firm, "company", "registrations", "people"];
}

// Rows left blank are dropped; a started row must be complete.
export function registrationProblem(rows, stateRegistrations) {
	for (const [index, row] of rows.entries()) {
		const started = row.registration_type || row.registration_number.trim();
		if (!started) continue;
		if (!row.registration_type)
			return `Registration ${index + 1}: choose which registration it is.`;
		if (!row.registration_number.trim()) return `Registration ${index + 1}: enter its number.`;
		if (stateRegistrations.includes(row.registration_type) && !row.state) {
			return `Registration ${index + 1}: choose the state of the ${
				row.registration_type
			} registration.`;
		}
	}
	return "";
}

// Where setup starts the company step. After ERPNext's own setup there is usually a company
// already, and for an organisation it is the one meant; for a firm it is the firm's own, never its
// client's, so a firm starts on a new company.
export function companyDefault(accountType, openCompanies, canCreate) {
	if (accountType === "CA/CS Firm" && canCreate) {
		// The one company there is the firm's own, named in ERPNext's setup: its name, not asked again.
		return { choice: "new", company: "", firmName: openCompanies.length === 1 ? openCompanies[0] : "" };
	}
	if (openCompanies.length || !canCreate) {
		return { choice: "existing", company: openCompanies.length === 1 ? openCompanies[0] : "" };
	}
	return { choice: "new", company: "" };
}

export function setupAnswers(answers, companyChoice) {
	return {
		account_type: answers.account_type,
		firm_name: answers.account_type === "CA/CS Firm" ? answers.firm_name.trim() : "",
		client_name: answers.account_type === "CA/CS Firm" ? answers.client_name.trim() : "",
		new_company: companyChoice === "new" ? answers.new_company.trim() : "",
		company: companyChoice === "existing" ? answers.company : "",
		company_type: answers.company_type,
		agm_date: answers.agm_date || "",
		registrations: answers.registrations
			.filter((row) => row.registration_type && row.registration_number.trim())
			.map((row) => ({
				registration_type: row.registration_type,
				registration_number: row.registration_number.trim(),
				state: row.state || "",
			})),
		responsible: answers.responsible,
		reviewer: answers.reviewer || "",
	};
}

// A GSTIN starts with its state's two-digit GST code.
const GST_STATE_CODES = {
	"01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
	"05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
	"10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
	"15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
	"20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
	"26": "Dadra and Nagar Haveli and Daman and Diu", "27": "Maharashtra", "29": "Karnataka",
	"30": "Goa", "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
	"35": "Andaman and Nicobar Islands", "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh",
}; // prettier-ignore

export const stateFromGstin = (number) => GST_STATE_CODES[(number || "").trim().slice(0, 2)] || "";

// Last year's AGM, asked of a company whose type has filings due after it.
export function agmQuestion(companyType, agmCompanyTypes, lastYearEnd) {
	if (!agmCompanyTypes?.includes(companyType)) return null;
	const year = new Date(`${lastYearEnd}T00:00:00`).getFullYear();
	return {
		label: `AGM for the year ended 31 March ${year}`,
		description:
			"AOC-4, MGT-7 and ADT-1 fall due from it. Leave it blank if the AGM is not held yet; add it on the company's page when it is.",
	};
}
