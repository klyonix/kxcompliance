// Values the server writes into the page (kxcompliance.api.boot), read once.
export const boot = {
	user: window.user || "Guest",
	siteName: window.site_name || "",
	userFullname: window.user_fullname || "",
	roles: window.roles || [],
	appName: window.app_name || "KlyONIX Compliance",
	appLogo: window.app_logo || "",
	companies: window.companies || [],
	// The site's date format setting, such as "dd-mm-yyyy".
	dateFormat: window.date_format || "",
	// "Organisation" or "CA/CS Firm", chosen in onboarding.
	accountType: window.account_type || "",
	// Whether sales and purchases are checked against licence rules here: always for an
	// organisation, and for a firm once a client of theirs is switched on.
	licenceCheckOn: Boolean(window.licence_check_on),
	// True for a manager on a site that has not been set up yet.
	setupNeeded: Boolean(window.setup_needed),
	// True until this person accepts the current privacy notice; the app shows it before anything.
	privacyNoticeDue: Boolean(window.privacy_notice_due),
	// Whose licences this person may check: Customer, Supplier or both.
	partyTypes: window.party_types || [],
	defaultCompany: window.default_company || "",
	// For someone at a firm's client: the client they belong to.
	client: window.client || "",
};

const COMPLIANCE_ROLES = [
	"Compliance Manager",
	"Compliance User",
	"Compliance Auditor",
	"System Manager",
];

const isStaff = () => COMPLIANCE_ROLES.some((role) => boot.roles.includes(role));

// Someone at a CA/CS firm's client: reads their companies' records and uploads documents.
export const isClientLogin = () => boot.roles.includes("Compliance Client") && !isStaff();

// Sales and Purchase Users without a compliance role see only the Licence Check.
export const checksOnly = () => !isStaff() && !isClientLogin();

// Client logins have no Desk.
export const mayUseDesk = () => !isClientLogin();

export const isManager = () =>
	boot.roles.includes("Compliance Manager") || boot.roles.includes("System Manager");

// Auditors read; the other compliance roles may also record.
export const mayRecord = () =>
	["Compliance Manager", "Compliance User", "System Manager"].some((role) =>
		boot.roles.includes(role)
	);

// The Licence Check, its rules and its log are offered where licences are checked.
export const licenceCheckOn = () => boot.licenceCheckOn;
