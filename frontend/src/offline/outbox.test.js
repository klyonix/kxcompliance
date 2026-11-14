import { afterEach, describe, expect, it } from "vitest";
import { connection, isWaiting, outbox } from "./outbox";
import { noteNoResponse, noteResponse } from "./reachability";

const reset = () =>
	Object.assign(outbox, {
		online: true,
		waiting: 0,
		pending: [],
		needsLook: [],
		sending: false,
	});

describe("where changes on this device stand", () => {
	afterEach(() => {
		reset();
		noteResponse({ status: 200 });
	});

	it("knows which records still have a change waiting", () => {
		Object.assign(outbox, { waiting: 1, pending: ["Compliance Task|CT-26-00012"] });
		expect(isWaiting("Compliance Task", "CT-26-00012")).toBe(true);
		expect(isWaiting("Compliance Task", "CT-26-00013")).toBe(false);
		expect(connection.value).toBe("sending");
	});

	it("puts a change that needs a look first, then offline, then the server", () => {
		Object.defineProperty(navigator, "onLine", { value: true, configurable: true });
		reset();
		expect(connection.value).toBe("saved");
		noteNoResponse();
		expect(connection.value).toBe("serverDown");
		outbox.online = false;
		expect(connection.value).toBe("offline");
		outbox.needsLook = [{ id: 1 }];
		expect(connection.value).toBe("needsLook");
	});
});
