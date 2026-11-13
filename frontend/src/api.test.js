import { describe, expect, it } from "vitest";
import { ApiError, call } from "./api";

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
});
