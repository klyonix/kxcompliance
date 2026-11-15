import { describe, expect, it } from "vitest";
import { ApiError, call, upload } from "./api";
import { noteResponse, server } from "./offline/reachability";

const answer = (status, body) => async () => ({
	ok: status === 200,
	status,
	statusText: "Error",
	json: async () => body,
});

describe("the API client", () => {
	it("returns the message on success and sends GET parameters in the address", async () => {
		let seen;
		const fetcher = async (url, init) => {
			seen = { url, init };
			return answer(200, { message: [1] })();
		};
		expect(await call("x.y", { a: "b" }, { fetcher })).toEqual([1]);
		expect(seen.url).toBe("/api/method/x.y?a=b");
		expect(seen.init.method).toBe("GET");
	});

	it("leaves a GET parameter that is not set out of the address", async () => {
		let seen;
		const fetcher = async (url) => {
			seen = url;
			return answer(200, { message: 1 })();
		};
		await call("x.y", { a: "b", client: undefined }, { fetcher });
		expect(seen).toBe("/api/method/x.y?a=b");
	});

	it("turns a refusal into an error carrying the server sentence, as text", async () => {
		const body = {
			exc_type: "ValidationError",
			_server_messages: JSON.stringify([
				JSON.stringify({ message: "<b>Due Day</b> must be set" }),
			]),
		};
		const error = await call("x.y", {}, { fetcher: answer(417, body) }).catch((err) => err);
		expect(error).toBeInstanceOf(ApiError);
		expect(error.message).toBe("Due Day must be set");
		expect(error.isNetwork).toBe(false);
	});

	it("reports no connection as a network error", async () => {
		const error = await call(
			"x.y",
			{},
			{
				fetcher: async () => {
					throw new TypeError("Failed");
				},
			}
		).catch((err) => err);
		expect(error.isNetwork).toBe(true);
	});

	it("never shows the server's raw exception text", async () => {
		const body = { exception: "pypdf.errors.PdfReadError: startxref not found" };
		const error = await call("x.y", {}, { fetcher: answer(500, body) }).catch((err) => err);
		expect(error.message).not.toContain("pypdf");
		expect(error.message).toContain("could not complete");
	});

	it("says a file the server fails on could not be read, by name", async () => {
		const body = { exc_type: "PdfReadError", exception: "pypdf.errors.PdfReadError" };
		const file = new File(["not a pdf"], "gst-return.pdf");
		const error = await upload(file, {
			doctype: "Compliance Task",
			docname: "CT-1",
			fetcher: answer(500, body),
		}).catch((err) => err);
		expect(error.message).toContain("could not read gst-return.pdf");
		const large = await upload(file, {
			doctype: "Compliance Task",
			docname: "CT-1",
			fetcher: answer(413, {}),
		}).catch((err) => err);
		expect(large.message).toBe("gst-return.pdf is too large to upload.");
	});

	it("treats a gateway error as no answer, and a saved copy as the server not answering", async () => {
		Object.defineProperty(navigator, "onLine", { value: true, configurable: true });
		const error = await call("x.y", {}, { fetcher: answer(502, {}) }).catch((err) => err);
		expect(error.isNetwork).toBe(true);
		expect(error.message).toBe("The server is not answering");
		noteResponse({ status: 200 });

		const saved = async () => ({
			...(await answer(200, { message: "old" })()),
			headers: new Headers({ "X-Served-From": "cache" }),
		});
		expect(await call("x.y", {}, { fetcher: saved })).toBe("old");
		expect(server.reachable).toBe(false);
		noteResponse({ status: 200 });
	});
});
