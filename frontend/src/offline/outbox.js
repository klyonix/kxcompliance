// What the screens show about the outbox, and sending it when the connection returns.
import { reactive } from "vue";
import { clearEntries } from "./db";
import { entries, flush } from "./queue";
import { probe, server, whenBack } from "./reachability";

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

// What a person is told when a change is kept on the device to send later.
export const SAVED_ON_DEVICE =
	"Saved on this device. It will be sent as soon as the server can be reached.";

// Online and the server answering: what actions that cannot wait for a connection need.
export const isConnected = () => outbox.online && server.reachable;

export async function sendWaiting() {
	if (outbox.sending || !isConnected()) return;
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
	window.addEventListener("online", async () => {
		outbox.online = true;
		// Back online says nothing about the server; ask it before sending.
		if (await probe()) sendWaiting();
	});
	whenBack(sendWaiting);
	window.addEventListener("offline", () => {
		outbox.online = false;
	});
	refresh().then(sendWaiting);
}
