import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { APIRequestContext, Browser, BrowserContext, Page, Route } from "@playwright/test";

/** Who a scene signs in as: the site's Administrator (a manager), or a test user. */
export type Persona = "manager" | "Compliance User" | "Sales User";
export type Width = "desktop" | "phone";

const VIEWPORTS: Record<Width, { width: number; height: number }> = {
	desktop: { width: 1280, height: 800 },
	phone: { width: 375, height: 812 },
};
/** Enough for frappe-ui transitions and toasts to finish appearing. */
const SETTLE_MS = 400;
const BENCH = process.env.BENCH_PATH ?? resolve(import.meta.dirname, "../../../../..");

export interface Hold {
	release(): Promise<void>;
	abort(status?: number): Promise<void>;
}

export interface Scene {
	page: Page;
	context: BrowserContext;
	api: APIRequestContext;
	width: Width;
	goto(path: string): Promise<void>;
	/** Holds requests whose URL matches until released, or fails them from `abort` on. */
	hold(url: string | RegExp): Promise<Hold>;
	settle(ms?: number): Promise<void>;
	/** Creates a record through the REST API and deletes it when the scene closes. */
	insert(doctype: string, values: Record<string, unknown>): Promise<Record<string, unknown>>;
	/** Deletes a record the app created during this path when the scene closes. */
	track(doctype: string, name: string): void;
	/** Runs before the tracked records are deleted, for records made as a side effect. */
	onClose(cleanup: () => Promise<void>): void;
	close(): Promise<void>;
}

function credentials(persona: Persona): { usr: string; pwd: string } {
	if (persona === "manager") {
		// The local dev site's Administrator; the file holds one line ending in the password.
		const line = readFileSync(resolve(BENCH, ".dev-credentials"), "utf8").trim();
		return { usr: "Administrator", pwd: line.slice(line.lastIndexOf(": ") + 2) };
	}
	const users = JSON.parse(readFileSync(resolve(import.meta.dirname, ".users.json"), "utf8"));
	return users[persona];
}

export async function openScene(
	browser: Browser,
	baseURL: string,
	{ persona = "manager", width = "desktop" }: { persona?: Persona; width?: Width } = {}
): Promise<Scene> {
	const context = await browser.newContext({
		baseURL,
		viewport: VIEWPORTS[width],
		isMobile: width === "phone",
		hasTouch: width === "phone",
		colorScheme: "light",
		// The app's service worker answers reads itself, out of reach of page.route.
		serviceWorkers: "block",
	});
	const api = context.request;
	const login = await api.post("/api/method/login", { form: credentials(persona) });
	if (!login.ok()) throw new Error(`Sign-in as ${persona} failed: ${login.status()}`);
	const page = await context.newPage();
	const created: { doctype: string; name: string }[] = [];
	const cleanups: (() => Promise<void>)[] = [];
	// Once the app has loaded, the session expects its CSRF token on writes.
	const csrf = async (): Promise<Record<string, string>> => {
		const token = await page.evaluate(() => (window as { csrf_token?: string }).csrf_token).catch(() => "");
		return token ? { "X-Frappe-CSRF-Token": token } : {};
	};

	return {
		page,
		context,
		api,
		width,
		async goto(path) {
			await page.goto(`/compliance${path}`);
		},
		async hold(url) {
			// Stays routed for the scene's life: unrouting would let a held request through.
			const held: Route[] = [];
			let status: number | null = null;
			let passing = false;
			const fail = (route: Route) =>
				route.fulfill({
					status: status ?? 500,
					contentType: "application/json",
					body: JSON.stringify({ exc_type: "ServerError", message: "Something went wrong" }),
				});
			await page.route(url, async (route) => {
				if (passing) await route.continue();
				else if (status === null) held.push(route);
				else await fail(route);
			});
			return {
				async release() {
					passing = true;
					await Promise.all(held.splice(0).map((route) => route.continue().catch(() => undefined)));
				},
				async abort(next = 500) {
					status = next;
					await Promise.all(held.splice(0).map((route) => fail(route).catch(() => undefined)));
				},
			};
		},
		async settle(ms = SETTLE_MS) {
			await page.waitForTimeout(ms);
		},
		async insert(doctype, values) {
			const response = await api.post(`/api/v2/document/${encodeURIComponent(doctype)}`, {
				data: values,
				headers: await csrf(),
			});
			if (!response.ok()) throw new Error(`${doctype}: ${await response.text()}`);
			const { data } = await response.json();
			created.push({ doctype, name: data.name });
			return data;
		},
		track(doctype, name) {
			created.push({ doctype, name });
		},
		onClose(cleanup) {
			cleanups.push(cleanup);
		},
		async close() {
			for (const cleanup of cleanups) await cleanup().catch(() => undefined);
			for (const { doctype, name } of created.reverse()) {
				const path = `/api/v2/document/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`;
				const response = await api.delete(path, { headers: await csrf() });
				// A record left behind skews every later screenshot, so say so loudly.
				if (!response.ok() && response.status() !== 404) console.warn(`Could not delete ${doctype} ${name}: ${await response.text()}`);
			}
			await context.close();
		},
	};
}
