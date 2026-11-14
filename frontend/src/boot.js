// Values the server writes into the page (compliance_plus.api.boot), read once.
export const boot = {
	user: window.user || "Guest",
	userFullname: window.user_fullname || "",
	roles: window.roles || [],
	appName: window.app_name || "Compliance Plus",
	appLogo: window.app_logo || "",
	companies: window.companies || [],
	// Whose licences this person may check: Customer, Supplier or both.
	partyTypes: window.party_types || [],
	defaultCompany: window.default_company || "",
};

const COMPLIANCE_ROLES = [
	"Compliance Manager",
	"Compliance User",
	"Compliance Auditor",
	"System Manager",
];

// Sales and Purchase Users without a compliance role see only the Licence Check.
export const checksOnly = () => !COMPLIANCE_ROLES.some((role) => boot.roles.includes(role));

export const isManager = () =>
	boot.roles.includes("Compliance Manager") || boot.roles.includes("System Manager");

// Auditors read; the other compliance roles may also record.
export const mayRecord = () =>
	["Compliance Manager", "Compliance User", "System Manager"].some((role) =>
		boot.roles.includes(role)
	);
