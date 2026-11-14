import { beforeEach, describe, expect, it, vi } from "vitest";

// A stand-in for navigator.serviceWorker and its registration, driven by the test.
class Events {
	constructor() {
		this.handlers = {};
	}
	addEventListener(name, handler) {
		(this.handlers[name] ||= []).push(handler);
	}
	emit(name) {
		for (const handler of this.handlers[name] || []) handler();
	}
}

function fakeWorker(state = "installing") {
	const worker = new Events();
	worker.state = state;
	worker.postMessage = vi.fn();
	return worker;
}

function fakeContainer({ controlled = true, waiting = null } = {}) {
	const registration = new Events();
	registration.waiting = waiting;
	registration.installing = null;
	registration.update = vi.fn(async () => {});
	const container = new Events();
	container.controller = controlled ? {} : null;
	container.register = vi.fn(async () => registration);
	return { container, registration };
}

let updates;
beforeEach(async () => {
	vi.resetModules();
	updates = await import("./updates");
});

describe("new versions of the app", () => {
	it("offers a reload once a new build has installed behind the running one", async () => {
		const { container, registration } = fakeContainer();
		await updates.watchForUpdates({ container });
		expect(updates.update.ready).toBe(false);

		const worker = fakeWorker();
		registration.installing = worker;
		registration.emit("updatefound");
		worker.state = "installed";
		worker.emit("statechange");
		expect(updates.update.ready).toBe(true);
	});

	it("offers nothing on the very first install", async () => {
		const { container, registration } = fakeContainer({ controlled: false });
		await updates.watchForUpdates({ container });
		const worker = fakeWorker();
		registration.installing = worker;
		registration.emit("updatefound");
		worker.state = "installed";
		worker.emit("statechange");
		expect(updates.update.ready).toBe(false);
	});

	it("offers a build that was already waiting when the page opened", async () => {
		const { container } = fakeContainer({ waiting: fakeWorker("installed") });
		await updates.watchForUpdates({ container });
		expect(updates.update.ready).toBe(true);
	});

	it("hands over to the new build and reloads only the tab that asked", async () => {
		const waiting = fakeWorker("installed");
		const { container } = fakeContainer({ waiting });
		const reload = vi.fn();
		await updates.watchForUpdates({ container, reload });

		updates.applyUpdate({ reload });
		expect(waiting.postMessage).toHaveBeenCalledWith({ type: "SKIP_WAITING" });
		expect(reload).not.toHaveBeenCalled();
		container.emit("controllerchange");
		expect(reload).toHaveBeenCalledTimes(1);
	});

	it("lets another tab's update offer a reload here instead of forcing one", async () => {
		const { container } = fakeContainer();
		const reload = vi.fn();
		await updates.watchForUpdates({ container, reload });
		container.emit("controllerchange");
		expect(reload).not.toHaveBeenCalled();
		expect(updates.update.ready).toBe(true);
		updates.applyUpdate({ reload });
		expect(reload).toHaveBeenCalledTimes(1);
	});
});
