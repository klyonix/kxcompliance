// What the screens show about the outbox, and sending it when the connection returns.
import { reactive } from "vue";
import { clearEntries } from "./db";
import { entries, flush } from "./queue";

export const outbox = reactive({
	online: typeof navigator === "undefined" ? true : navigator.onLine,
	waiting: 0,
	needsLook: [],
	sending: false,
});

export async function refresh() {
	const all = await entries();
	outbox.waiting = all.filter((entry) => entry.status === "waiting").length;
	outbox.needsLook = all.filter((entry) => entry.status !== "waiting");
}

export async function sendWaiting() {
	if (outbox.sending || !outbox.online) return;
	outbox.sending = true;
	try {
		await flush();
	} finally {
		outbox.sending = false;
		await refresh();
	}
}

export async function clearOutbox() {
	await clearEntries();
	await refresh();
}

export function watchConnection() {
	window.addEventListener("online", () => {
		outbox.online = true;
		sendWaiting();
	});
	window.addEventListener("offline", () => {
		outbox.online = false;
	});
	refresh().then(sendWaiting);
}
