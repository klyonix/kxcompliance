import { describe, expect, it } from "vitest";
import { realtimeUrl } from "./socket";

describe("the realtime address", () => {
	it("uses the development port when the site is served on one, else the site's own address", () => {
		expect(
			realtimeUrl(
				{ hostname: "compliance.localhost", port: "8001", protocol: "http:" },
				9001,
				"compliance.localhost"
			)
		).toBe("http://compliance.localhost:9001/compliance.localhost");
		expect(
			realtimeUrl(
				{ hostname: "acme.example.com", port: "", protocol: "https:" },
				9000,
				"acme.example.com"
			)
		).toBe("https://acme.example.com/acme.example.com");
	});
});
