import { createRouter, createWebHistory } from "vue-router";

export const routes = [
	{ path: "/", name: "MyWork", component: () => import("./pages/MyWork.vue") },
	{ path: "/account", name: "Account", component: () => import("./pages/Account.vue") },
	{ path: "/:pathMatch(.*)*", redirect: "/" },
];

export default createRouter({ history: createWebHistory("/compliance"), routes });
