// Whether the server is answering, as distinct from whether the device is online. A phone can
// have a signal while the site is down, restarting or behind a broken gateway; the app then
// works from what it saved, exactly as when offline, and says so.
import { reactive } from "vue";

export const PROBE_EVERY_MS = 15000;
// What a gateway answers when the app server behind it does not.
export const GATEWAY_STATUSES = [502, 503, 504];

export const server = reactive({ reachable: true, downSince: null });

const listeners = [];
let timer = null;

const deviceOnline = () => (typeof navigator === "undefined" ? true : navigator.onLine);

// Called once the server answers again, to send what waited.
export function whenBack(listener) {
	listeners.push(listener);
}

function markDown() {
	if (server.reachable) {
		server.reachable = false;
		server.downSince = Date.now();
	}
	clearTimeout(timer);
	timer = setTimeout(probe, PROBE_EVERY_MS);
}

function markUp() {
	clearTimeout(timer);
	timer = null;
	if (server.reachable) return;
	server.reachable = true;
	server.downSince = null;
	for (const listener of listeners) listener();
}

// The page's requests report here. Offline is the browser's to say, so only an online device
// can find the server unreachable.
export function noteResponse({ status, fromCache = false }) {
	if (fromCache || GATEWAY_STATUSES.includes(status)) {
		if (deviceOnline()) markDown();
		return;
	}
	markUp();
}

export function noteNoResponse() {
	if (deviceOnline()) markDown();
}

// Ask the server directly; the service worker leaves this one request alone.
export async function probe({ fetcher = fetch } = {}) {
	try {
		const response = await fetcher("/api/method/ping", {
			cache: "no-store",
			credentials: "same-origin",
		});
		noteResponse({ status: response.status });
	} catch {
		noteNoResponse();
	}
	return server.reachable;
}

// Why something could not be shown: the device is offline, or the server is not answering.
export function notLoaded(what, verb = "loaded") {
	const why = deviceOnline() ? "The server is not answering" : "You are offline";
	return `${why}, and ${what} has not been ${verb} on this device yet.`;
}
