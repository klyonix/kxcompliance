import "./index.css";

import { createApp } from "vue";
import { FrappeUI, FrappeUIProvider, frappeRequest, setConfig } from "frappe-ui";
import { h } from "vue";

import App from "./App.vue";
import { getSocket } from "./socket";
import { applyAppearance, readAppearance } from "./lib/appearance";
import { setLanguage, t } from "./lib/i18n";
import router from "./router";
import { watchConnection } from "./offline/outbox";
import { watchForUpdates } from "./offline/updates";

// frappe-ui's resources (used by Frappe's shared components, such as notifications) call the
// site's API through Frappe's own request helper.
setConfig("resourceFetcher", frappeRequest);
applyAppearance(readAppearance());

// The live connection to Frappe's realtime server, for Frappe's shared components (notifications,
// a record's activity) and the app's lists. frappe-ui's `$socket` throws until one is set.
const socket = getSocket();
const app = createApp({ render: () => h(FrappeUIProvider, null, { default: () => h(App) }) });
app.config.globalProperties.$socket = socket;
// Every template may write t("...") for the reader's language (lib/i18n.js).
app.config.globalProperties.t = t;
setLanguage(window.lang);
app.provide("socket", socket).use(router).use(FrappeUI).mount("#app");
watchConnection();

if ("serviceWorker" in navigator && import.meta.env.PROD) {
	watchForUpdates();
}
