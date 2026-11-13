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
	{ path: "/:pathMatch(.*)*", redirect: "/" },
];

export default createRouter({ history: createWebHistory("/compliance"), routes });
