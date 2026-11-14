import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
	PROBE_EVERY_MS,
	noteNoResponse,
	noteResponse,
	probe,
	server,
	whenBack,
} from "./reachability";

const setOnline = (value) =>
	Object.defineProperty(navigator, "onLine", { value, configurable: true });

describe("whether the server answers", () => {
	beforeEach(() => {
		vi.useFakeTimers();
		setOnline(true);
		noteResponse({ status: 200 });
	});
	afterEach(() => {
		noteResponse({ status: 200 });
		vi.useRealTimers();
	});

	it("is unreachable when an online device gets no answer, a gateway error or a saved copy", () => {
		noteNoResponse();
		expect(server.reachable).toBe(false);
		noteResponse({ status: 200 });
		expect(server.reachable).toBe(true);
		noteResponse({ status: 502 });
		expect(server.reachable).toBe(false);
		noteResponse({ status: 200 });
		noteResponse({ status: 200, fromCache: true });
		expect(server.reachable).toBe(false);
	});

	it("leaves an offline device to the browser's own offline notice", () => {
		setOnline(false);
		noteNoResponse();
		noteResponse({ status: 200, fromCache: true });
		expect(server.reachable).toBe(true);
	});

	it("counts a refusal as an answer", () => {
		noteNoResponse();
		noteResponse({ status: 417 });
		expect(server.reachable).toBe(true);
	});

	it("asks again on its own and sends what waited once the server is back", async () => {
		const back = vi.fn();
		whenBack(back);
		noteNoResponse();
		const since = server.downSince;
		noteNoResponse();
		expect(server.downSince).toBe(since);

		let answers = false;
		const fetcher = vi.fn(async () => {
			if (!answers) throw new TypeError("Failed to fetch");
			return { status: 200 };
		});
		expect(await probe({ fetcher })).toBe(false);
		expect(back).not.toHaveBeenCalled();
		answers = true;
		expect(await probe({ fetcher })).toBe(true);
		expect(back).toHaveBeenCalledTimes(1);
		expect(fetcher).toHaveBeenCalledWith(
			"/api/method/ping",
			expect.objectContaining({ cache: "no-store" })
		);
		expect(PROBE_EVERY_MS).toBeGreaterThan(0);
	});
});
