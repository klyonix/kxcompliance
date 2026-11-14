import { createRouter, createWebHistory } from "vue-router";
import { boot, checksOnly, isClientLogin, isManager } from "./boot";
import { CLIENT_ROUTES } from "./navigation";
import { noteNoResponse } from "./offline/reachability";

export const routes = [
	{ path: "/", name: "MyWork", component: () => import("./pages/MyWork.vue") },
	{ path: "/setup", name: "Onboarding", component: () => import("./pages/Onboarding.vue") },
	{ path: "/search", name: "Search", component: () => import("./pages/Search.vue") },
	{ path: "/overview", name: "Overview", component: () => import("./pages/Overview.vue") },
	{ path: "/account", name: "Account", component: () => import("./pages/Account.vue") },
	{ path: "/settings", name: "Settings", component: () => import("./pages/Settings.vue") },
	{ path: "/help", name: "Help", component: () => import("./pages/Help.vue") },
	{ path: "/reports", name: "Reports", component: () => import("./pages/Reports.vue") },
	{
		path: "/reports/:report",
		name: "Report",
		component: () => import("./pages/Report.vue"),
		props: true,
	},
	{ path: "/register", name: "Register", component: () => import("./pages/Register.vue") },
	{ path: "/companies", name: "Companies", component: () => import("./pages/Companies.vue") },
	{
		path: "/companies/new",
		name: "CompanyNew",
		component: () => import("./pages/CompanyForm.vue"),
	},
	{
		path: "/companies/:company",
		name: "Company",
		component: () => import("./pages/CompanyForm.vue"),
		props: true,
	},
	{
		path: "/signatories",
		name: "Signatories",
		component: () => import("./pages/Signatories.vue"),
	},
	{
		path: "/signatories/new",
		name: "SignatoryNew",
		component: () => import("./pages/SignatoryForm.vue"),
	},
	{
		path: "/signatories/:name",
		name: "Signatory",
		component: () => import("./pages/SignatoryForm.vue"),
		props: true,
	},
	{
		path: "/register/new",
		name: "ItemNew",
		component: () => import("./pages/ItemForm.vue"),
	},
	{
		path: "/register/:name/edit",
		name: "ItemEdit",
		component: () => import("./pages/ItemForm.vue"),
		props: true,
	},
	{
		path: "/settings/people",
		name: "People",
		component: () => import("./pages/People.vue"),
	},
	{
		path: "/settings/item-types",
		name: "ItemTypes",
		component: () => import("./pages/ItemTypes.vue"),
	},
	{
		path: "/settings/item-types/new",
		name: "ItemTypeNew",
		component: () => import("./pages/ItemTypeForm.vue"),
	},
	{
		path: "/settings/item-types/:name",
		name: "ItemType",
		component: () => import("./pages/ItemTypeForm.vue"),
		props: true,
	},
	{
		path: "/settings/obligations",
		name: "ObligationLibrary",
		component: () => import("./pages/ObligationLibrary.vue"),
	},
	{
		path: "/settings/obligations/new",
		name: "ObligationNew",
		component: () => import("./pages/ObligationForm.vue"),
	},
	{
		// Obligation names may hold a slash ("TDS/TCS Payment").
		path: "/settings/obligations/:name(.*)",
		name: "Obligation",
		component: () => import("./pages/ObligationForm.vue"),
		props: true,
	},
	{
		path: "/register/:name",
		name: "ComplianceItem",
		component: () => import("./pages/ComplianceItem.vue"),
		props: true,
	},
	{
		path: "/home",
		name: "ClientHome",
		component: () => import("./pages/Client.vue"),
		props: () => ({ name: boot.client }),
	},
	{ path: "/clients", name: "Clients", component: () => import("./pages/Clients.vue") },
	{
		path: "/clients/new",
		name: "ClientNew",
		component: () => import("./pages/ClientForm.vue"),
	},
	{
		path: "/clients/:name/edit",
		name: "ClientEdit",
		component: () => import("./pages/ClientForm.vue"),
		props: true,
	},
	{
		path: "/clients/import",
		name: "BulkSetup",
		component: () => import("./pages/BulkSetup.vue"),
	},
	{
		path: "/clients/:name",
		name: "Client",
		component: () => import("./pages/Client.vue"),
		props: true,
	},
	{
		path: "/requests/:name",
		name: "DocumentRequest",
		component: () => import("./pages/DocumentRequest.vue"),
		props: true,
	},
	{ path: "/filings", name: "Filings", component: () => import("./pages/Filings.vue") },
	{
		path: "/calendar",
		name: "MonthCalendar",
		component: () => import("./pages/MonthCalendar.vue"),
	},
	{
		path: "/filings/bulk",
		name: "BulkFiling",
		component: () => import("./pages/BulkFiling.vue"),
	},
	{
		path: "/filings/extensions",
		name: "Extensions",
		component: () => import("./pages/Extensions.vue"),
	},
	{
		path: "/filings/extensions/new",
		name: "ExtensionNew",
		component: () => import("./pages/ExtensionForm.vue"),
	},
	{
		path: "/filings/extensions/:name",
		name: "Extension",
		component: () => import("./pages/ExtensionForm.vue"),
		props: true,
	},
	{
		path: "/filings/event",
		name: "RecordEvent",
		component: () => import("./pages/RecordEvent.vue"),
	},
	{
		path: "/filings/:name",
		name: "ComplianceTask",
		component: () => import("./pages/ComplianceTask.vue"),
		props: true,
	},
	{ path: "/legal", name: "Legal", component: () => import("./pages/Legal.vue") },
	{ path: "/legal/new", name: "NewNotice", component: () => import("./pages/NewNotice.vue") },
	{
		path: "/legal/case/:name",
		name: "LegalCase",
		component: () => import("./pages/LegalCase.vue"),
		props: true,
	},
	{
		path: "/legal/trademark/:name",
		name: "Trademark",
		component: () => import("./pages/Trademark.vue"),
		props: true,
	},
	{
		path: "/licence-check",
		name: "LicenceCheck",
		component: () => import("./pages/LicenceCheck.vue"),
	},
	{ path: "/:pathMatch(.*)*", redirect: "/" },
];

// Screens for Compliance Managers only; the server refuses the rest anyway.
const MANAGER_ROUTES = [
	"Overview",
	"BulkSetup",
	"Settings",
	"ClientNew",
	"ClientEdit",
	"Companies",
	"CompanyNew",
	"Company",
	"People",
	"ItemTypes",
	"ItemTypeNew",
	"ItemType",
	"ObligationLibrary",
	"ObligationNew",
	"Obligation",
	"Extensions",
	"ExtensionNew",
	"Extension",
];

const router = createRouter({ history: createWebHistory("/compliance"), routes });

// Someone here only for the Licence Check is kept to it (the server refuses the rest anyway).
router.beforeEach((to) => {
	// A manager on a new site sets it up before anything else.
	if (boot.setupNeeded && to.name !== "Onboarding") return { name: "Onboarding" };
	if (!boot.setupNeeded && to.name === "Onboarding") return { name: "MyWork" };
	if (isClientLogin()) {
		if (!CLIENT_ROUTES.includes(to.name)) return { name: "ClientHome" };
		return;
	}
	if (to.name === "ClientHome") return { name: "MyWork" };
	if (checksOnly() && !["LicenceCheck", "Account", "Help"].includes(to.name)) {
		return { name: "LicenceCheck" };
	}
	if (MANAGER_ROUTES.includes(to.name) && !isManager()) {
		return { name: "MyWork" };
	}
});

// A screen's code that cannot be fetched means the server is not answering (or the device is offline).
router.onError((error) => {
	if (error instanceof TypeError) noteNoResponse();
});

export default router;
