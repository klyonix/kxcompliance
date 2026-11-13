// Values the server writes into the page (compliance_plus.api.boot), read once.
export const boot = {
	user: window.user || "Guest",
	userFullname: window.user_fullname || "",
	roles: window.roles || [],
	appName: window.app_name || "Compliance Plus",
	appLogo: window.app_logo || "",
};

export const isManager = () =>
	boot.roles.includes("Compliance Manager") || boot.roles.includes("System Manager");
