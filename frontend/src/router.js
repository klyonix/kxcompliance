import { createRouter, createWebHistory } from "vue-router";

export const routes = [
	{ path: "/", name: "MyWork", component: () => import("./pages/MyWork.vue") },
	{ path: "/account", name: "Account", component: () => import("./pages/Account.vue") },
	{ path: "/register", name: "Register", component: () => import("./pages/Register.vue") },
	{
		path: "/register/:name",
		name: "ComplianceItem",
		component: () => import("./pages/ComplianceItem.vue"),
		props: true,
	},
	{ path: "/filings", name: "Filings", component: () => import("./pages/Filings.vue") },
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
	{ path: "/:pathMatch(.*)*", redirect: "/" },
];

export default createRouter({ history: createWebHistory("/compliance"), routes });
