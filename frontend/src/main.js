import "./index.css";

import { createApp } from "vue";
import { FrappeUI, FrappeUIProvider } from "frappe-ui";
import { h } from "vue";

import App from "./App.vue";
import router from "./router";
import { watchConnection } from "./offline/outbox";
import { watchForUpdates } from "./offline/updates";

createApp({ render: () => h(FrappeUIProvider, null, { default: () => h(App) }) })
	.use(router)
	.use(FrappeUI)
	.mount("#app");
watchConnection();

if ("serviceWorker" in navigator && import.meta.env.PROD) {
	watchForUpdates();
}
