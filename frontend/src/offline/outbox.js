// What the screens show about the outbox, and sending it when the connection returns.
import { computed, reactive } from "vue";
import { clearEntries } from "./db";
import { entries, flush } from "./queue";
import { probe, server, whenBack } from "./reachability";

export const outbox = reactive({
	online: typeof navigator === "undefined" ? true : navigator.onLine,
	waiting: 0,
	// "doctype|name" of each record with a change waiting to be sent.
	pending: [],
	needsLook: [],
	sending: false,
});

export async function refresh() {
	const all = await entries();
	const waiting = all.filter((entry) => entry.status === "waiting");
	outbox.waiting = waiting.length;
	outbox.pending = waiting.map((entry) => `${entry.doctype}|${entry.name}`);
	outbox.needsLook = all.filter((entry) => entry.status !== "waiting");
}

// What a person is told when a change is kept on the device to send later.
export const SAVED_ON_DEVICE =
	"Saved on this device. It will be sent as soon as the server can be reached.";

// Whether a record still has a change on this device; the screens follow this, not a flag of their own.
export const isWaiting = (doctype, name) => outbox.pending.includes(`${doctype}|${name}`);

// Where changes on this device stand, decided once for the banner and the side bar:
// "needsLook" | "offline" | "serverDown" | "sending" | "saved".
export const connection = computed(() => {
	if (outbox.needsLook.length) return "needsLook";
	if (!outbox.online) return "offline";
	if (!server.reachable) return "serverDown";
	if (outbox.sending || outbox.waiting) return "sending";
	return "saved";
});

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
