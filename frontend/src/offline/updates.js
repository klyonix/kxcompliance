// New versions of the app. The service worker installs a new build in the background and then
// waits, so a page is never swapped mid-task; the app offers a reload and the new worker takes
// over when the person chooses.
import { reactive } from "vue";

export const CHECK_EVERY_MS = 60 * 60 * 1000;

export const update = reactive({ ready: false });

let registration = null;
let reloading = false;

function offerWhenInstalled(worker, container) {
	worker?.addEventListener("statechange", () => {
		// The very first install has nothing to replace, so there is nothing to offer.
		if (worker.state === "installed" && container.controller) update.ready = true;
	});
}

export async function watchForUpdates({
	container = navigator.serviceWorker,
	reload = () => window.location.reload(),
} = {}) {
	registration = await container.register("/compliance_sw.js", { scope: "/compliance" });
	if (registration.waiting && container.controller) update.ready = true;
	registration.addEventListener("updatefound", () =>
		offerWhenInstalled(registration.installing, container)
	);

	// Another tab may apply the update; this one keeps working on the old build and offers
	// the reload too, rather than throwing away what someone is typing.
	container.addEventListener("controllerchange", () => {
		if (reloading) reload();
		else update.ready = true;
	});

	const check = () => registration.update().catch(() => {});
	setInterval(check, CHECK_EVERY_MS);
	document.addEventListener("visibilitychange", () => {
		if (document.visibilityState === "visible") check();
	});
}

// Changes waiting to be sent are kept in the browser's storage, so a reload loses none of them.
export function applyUpdate({ reload = () => window.location.reload() } = {}) {
	const waiting = registration?.waiting;
	if (waiting) {
		reloading = true;
		waiting.postMessage({ type: "SKIP_WAITING" });
	} else {
		reload();
	}
}
