import { defineConfig } from "@playwright/test";
import { resolve } from "node:path";

/**
 * Captures every state of the compliance app as a screenshot, walking the machines
 * under `flows/`. Not a test suite: no retries, one worker, against the local dev
 * site (BASE_URL), which must be running.
 */
const baseURL = process.env.BASE_URL ?? "http://compliance.localhost:8001";

export const OUT_DIR = resolve(import.meta.dirname, "out");

export default defineConfig({
	testDir: import.meta.dirname,
	testMatch: /capture\.spec\.ts/,
	outputDir: resolve(import.meta.dirname, ".runs"),
	retries: 0,
	workers: 1,
	timeout: 20 * 60_000,
	expect: { timeout: 10_000 },
	reporter: [["list"]],
	use: {
		baseURL,
		// The installed Chrome, so no browser download is needed.
		channel: "chrome",
		actionTimeout: 15_000,
		navigationTimeout: 30_000,
	},
});
