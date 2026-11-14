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
	{ path: "/register", name: "Register", component: () => import("./pages/Register.vue") },
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
const MANAGER_ROUTES = ["Overview", "BulkSetup", "Settings", "ClientNew", "ClientEdit"];

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
	if (checksOnly() && !["LicenceCheck", "Account"].includes(to.name)) {
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
