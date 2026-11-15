// The person's notifications from this app (Frappe's Notification Log): one feed for the bell
// in the side bar, the bell in each page's header on a phone, and the panel they open.
import { ref } from "vue";
import { useNotifications } from "@framework/ui/components/Notifications/index.ts";

const REFRESH_MS = 2 * 60 * 1000;

let controller = null;
export const panelOpen = ref(false);

export function notifications() {
	if (!controller) {
		controller = useNotifications({ appName: "kxcompliance" });
		// No live connection to the server here, so the feed checks in every few minutes.
		setInterval(() => {
			if (document.visibilityState === "visible") controller.reload();
		}, REFRESH_MS);
	}
	return controller;
}

export function openPanel() {
	panelOpen.value = true;
	notifications().markSeen();
}
