import "./index.css";

import { createApp } from "vue";
import { FrappeUI, FrappeUIProvider, frappeRequest, setConfig } from "frappe-ui";
import { h } from "vue";

import App from "./App.vue";
import { applyAppearance, readAppearance } from "./lib/appearance";
import router from "./router";
import { watchConnection } from "./offline/outbox";
import { watchForUpdates } from "./offline/updates";

// frappe-ui's resources (used by Frappe's shared components, such as notifications) call the
// site's API through Frappe's own request helper.
setConfig("resourceFetcher", frappeRequest);
applyAppearance(readAppearance());

createApp({ render: () => h(FrappeUIProvider, null, { default: () => h(App) }) })
	.use(router)
	.use(FrappeUI)
	.mount("#app");
watchConnection();

if ("serviceWorker" in navigator && import.meta.env.PROD) {
	watchForUpdates();
}
