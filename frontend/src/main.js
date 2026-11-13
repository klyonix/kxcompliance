import "./index.css";

import { createApp } from "vue";
import { FrappeUI, FrappeUIProvider } from "frappe-ui";
import { h } from "vue";

import App from "./App.vue";
import router from "./router";
import { watchConnection } from "./offline/outbox";

createApp({ render: () => h(FrappeUIProvider, null, { default: () => h(App) }) })
	.use(router)
	.use(FrappeUI)
	.mount("#app");
watchConnection();

if ("serviceWorker" in navigator && import.meta.env.PROD) {
	navigator.serviceWorker.register("/compliance_sw.js", { scope: "/compliance" });
}
