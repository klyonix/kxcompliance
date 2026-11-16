// Values the server writes into the page (kxcompliance.api.boot), read once.
import { reactive } from "vue";

export const boot = {
	user: window.user || "Guest",
	siteName: window.site_name || "",
	userFullname: window.user_fullname || "",
	roles: window.roles || [],
	appName: window.app_name || "KlyONIX Compliance",
	appLogo: window.app_logo || "",
	// Reactive, so a company added in the app is offered at once (addCompany).
	companies: reactive(window.companies || []),
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
	// The language the person reads the app in (their Frappe language), such as "hi".
	lang: window.lang || "en",
	// For someone at a firm's client: the client they belong to.
	client: window.client || "",
	// A firm set up to bill, and someone ERPNext lets make invoices (an Accounts User).
	mayBill: Boolean(window.may_bill),
	// Whether the firm has set billing up; until then its managers open the setup from Billing.
	billingSetUp: Boolean(window.billing_set_up),
	// Added by other apps on the site (kxcompliance_boot): notices shown at the top of the app,
	// [{ text, theme, link_label, link_url }], and links on Account, [{ label, url, icon }].
	notices: window.notices || [],
	accountLinks: window.account_links || [],
	// Front-end plug-ins from other apps, [{ script, style }], loaded before the app starts (plugins.js).
	plugins: window.plugins || [],
	// Set by another app that keeps this person off the Desk.
	hideDesk: Boolean(window.hide_desk),
};

// The signed-in person's photo, changed from the profile popup or Account without a reload.
export const profile = reactive({ image: window.user_image || "" });

// A company just made or set up here joins the pickers without a reload, in name order.
export function addCompany(name) {
	if (!name || boot.companies.includes(name)) return;
	boot.companies.push(name);
	boot.companies.sort((a, b) => a.localeCompare(b));
}

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

// Client logins have no Desk, nor anyone another app keeps off it.
export const mayUseDesk = () => !isClientLogin() && !boot.hideDesk;

export const isManager = () =>
	boot.roles.includes("Compliance Manager") || boot.roles.includes("System Manager");

// Auditors read; the other compliance roles may also record.
export const mayRecord = () =>
	["Compliance Manager", "Compliance User", "System Manager"].some((role) =>
		boot.roles.includes(role)
	);

// The Licence Check, its rules and its log are offered where licences are checked.
export const licenceCheckOn = () => boot.licenceCheckOn;
