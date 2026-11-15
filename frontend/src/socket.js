// The live connection to Frappe's realtime server, as Frappe CRM makes it: on a development port
// when the site is served on one, else through the site's own address. Lists, notifications and
// a record's activity listen on it; without it they load as before and it keeps trying quietly.
import { io } from "socket.io-client";

export function realtimeUrl({ hostname, port, protocol }, socketioPort, siteName) {
	if (port) return `${protocol}//${hostname}:${socketioPort}/${siteName}`;
	return `${protocol}//${hostname}/${siteName}`;
}

let socket = null;

// One connection for the whole app.
export function getSocket() {
	socket = socket || initSocket();
	return socket;
}

// Calls `onChange` (at most once a second) when a record of `doctype` is saved or deleted by
// anyone; returns a function that stops listening.
export function watchDoctype(doctype, onChange) {
	const live = getSocket();
	let timer = null;
	const handler = (data) => {
		if (data?.doctype !== doctype) return;
		clearTimeout(timer);
		timer = setTimeout(onChange, 1000);
	};
	const subscribe = () => live.emit("doctype_subscribe", doctype);
	live.on("list_update", handler);
	live.on("connect", subscribe);
	if (live.connected) subscribe();
	return () => {
		clearTimeout(timer);
		live.off("list_update", handler);
		live.off("connect", subscribe);
	};
}

function initSocket() {
	const url = realtimeUrl(window.location, window.socketio_port || 9000, window.site_name);
	return io(url, {
		withCredentials: true,
		// Retry for good, with growing random gaps, so open tabs do not all reconnect at once.
		reconnectionDelay: 2000,
		reconnectionDelayMax: 30000,
		randomizationFactor: 0.5,
	});
}
