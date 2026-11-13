import "fake-indexeddb/auto";
import { beforeEach, describe, expect, it } from "vitest";
import { clearEntries } from "./db";
import { enqueue, entries, flush, retry, submit } from "./queue";

// A pretend server: answers in the order given; `offline` means no answer at all.
function server(...answers) {
	const calls = [];
	const fetcher = async (url, init) => {
		calls.push({ url, body: init.body });
		const answer = answers.shift();
		if (answer === "offline") throw new TypeError("Failed to fetch");
		return {
			ok: answer.status === 200,
			status: answer.status,
			statusText: "",
			json: async () => answer.body,
		};
	};
	return { fetcher, calls };
}
const ok = (message) => ({ status: 200, body: { message } });
const refused = (excType, text) => ({
	status: 417,
	body: {
		exc_type: excType,
		_server_messages: JSON.stringify([JSON.stringify({ message: text })]),
	},
});

const change = (name, extra = {}) => ({
	doctype: "Compliance Task",
	name,
	values: { status: "Ready for Review" },
	baseModified: "2026-11-14 10:00:00",
	...extra,
});

describe("the outbox", () => {
	beforeEach(() => clearEntries());

	it("sends straight away when online and keeps nothing", async () => {
		const { fetcher } = server(ok({ name: "CT-1", modified: "x" }));
		expect(await submit(change("CT-1"), { fetcher })).toEqual({
			queued: false,
			result: { name: "CT-1", modified: "x" },
		});
		expect(await entries()).toHaveLength(0);
	});

	it("keeps a change made offline and sends it, oldest first, when back online", async () => {
		expect((await submit(change("CT-1"), { fetcher: server("offline").fetcher })).queued).toBe(
			true
		);
		await enqueue(change("CT-2"));
		const { fetcher, calls } = server(ok({}), ok({}));
		expect(await flush({ fetcher })).toMatchObject({ sent: 2, conflicts: 0, failed: 0 });
		expect(calls.map((call) => JSON.parse(call.body).name)).toEqual(["CT-1", "CT-2"]);
		expect(await entries()).toHaveLength(0);
	});

	it("marks a change someone else overtook as needing a second look", async () => {
		await enqueue(change("CT-1"));
		const { fetcher } = server(
			refused("TimestampMismatchError", "was changed by someone else")
		);
		expect(await flush({ fetcher })).toMatchObject({ conflicts: 1 });
		const [entry] = await entries();
		expect(entry.status).toBe("conflict");
		expect(entry.error).toContain("changed by someone else");
	});

	it("keeps the server reason when a change is refused", async () => {
		await enqueue(change("CT-1"));
		await flush({
			fetcher: server(refused("ValidationError", "Fill in Proof before moving CT-1"))
				.fetcher,
		});
		const [entry] = await entries();
		expect(entry.status).toBe("failed");
		expect(entry.error).toBe("Fill in Proof before moving CT-1");
	});

	it("stops at a lost connection so the order is kept", async () => {
		await enqueue(change("CT-1"));
		await enqueue(change("CT-2"));
		const summary = await flush({ fetcher: server("offline").fetcher });
		expect(summary).toMatchObject({ sent: 0, stoppedOffline: true });
		expect((await entries()).map((entry) => entry.status)).toEqual(["waiting", "waiting"]);
	});

	it("uploads files first and saves with their address", async () => {
		const blob = new Blob(["receipt"], { type: "text/plain" });
		await enqueue(
			change("CT-1", {
				values: { acknowledgement_number: "AA1" },
				files: [{ field: "proof", blob, fileName: "ack.txt" }],
			})
		);
		const { fetcher, calls } = server(ok({ file_url: "/private/files/ack.txt" }), ok({}));
		await flush({ fetcher });
		expect(calls[0].url).toBe("/api/method/upload_file");
		expect(JSON.parse(calls[1].body).values).toEqual({
			acknowledgement_number: "AA1",
			proof: "/private/files/ack.txt",
		});
	});

	it("puts a change back in line against the newer record", async () => {
		await enqueue(change("CT-1"));
		await flush({ fetcher: server(refused("TimestampMismatchError", "changed")).fetcher });
		const [entry] = await entries();
		await retry(entry, "2026-11-14 11:00:00");
		const { fetcher, calls } = server(ok({}));
		await flush({ fetcher });
		expect(JSON.parse(calls[0].body).base_modified).toBe("2026-11-14 11:00:00");
		expect(await entries()).toHaveLength(0);
	});
});
