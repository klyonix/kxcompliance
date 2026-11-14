import { expect } from "@playwright/test";
import { setup } from "xstate";
import { atBothWidths, defineFlow } from "../flow";
import type { Hold, Scene } from "../scene";

type Event =
	| { type: "LOADS" }
	| { type: "FAILS" }
	| { type: "RETRY" }
	| { type: "PICK_WEEK" }
	| { type: "PICK_OVERDUE" }
	| { type: "SERVER_DOWN" }
	| { type: "GOES_OFFLINE" };

/**
 * My Work from the first paint: loading, failed, the list grouped by when things are due,
 * its tabs, and what the page keeps when the server stops answering or the device goes
 * offline. In the code: MyWork.vue's v-if chain over work.error, work.loading and rows,
 * stores/work.js, and ConnectionBanner.vue.
 */
const machine = setup({ types: { events: {} as Event } }).createMachine({
	id: "my-work",
	initial: "skeleton",
	states: {
		skeleton: {
			meta: { description: "My Work is loading: skeleton rows under the greeting." },
			on: { LOADS: "grouped", FAILS: "failed" },
		},
		failed: {
			meta: { description: "Loading My Work failed on the server: its message, and the Refresh button in the header." },
			on: { RETRY: "grouped" },
		},
		grouped: {
			meta: { description: "Everything the person holds or reviews, grouped into overdue, this week and later." },
			on: { PICK_WEEK: "thisWeek", PICK_OVERDUE: "overdueTab", SERVER_DOWN: "serverDown", GOES_OFFLINE: "offline" },
		},
		thisWeek: {
			meta: { description: "The This week tab: only what falls due in the next seven days." },
		},
		overdueTab: {
			meta: { description: "The Overdue tab when nothing is overdue." },
		},
		serverDown: {
			meta: { description: "A refresh the server did not answer: the list stays, and the banner says the server is not answering." },
		},
		offline: {
			meta: { description: "The device went offline: the list stays, and the banner says what was last loaded is shown." },
		},
	},
});

const holds = new WeakMap<Scene, Hold>();
const MY_WORK = "**/api/method/compliance_plus.api.my_work*";

async function expectRows(scene: Scene) {
	await expect(scene.page.getByText("This week", { exact: false }).first()).toBeVisible();
	await expect(scene.page.getByRole("link").filter({ hasText: "Sample GST demand appeal" })).toBeVisible();
}

const tab = (scene: Scene, name: RegExp) => scene.page.getByRole("radio", { name }).first();

export const myWork = atBothWidths(
	defineFlow<Event>({
		id: "my-work",
		title: "My Work",
		source: "frontend/src/pages/MyWork.vue, frontend/src/stores/work.js",
		machine,
		async enter(scene) {
			holds.set(scene, await scene.hold(MY_WORK));
			await scene.goto("/");
			await expect(scene.page.getByText(/^Good (morning|afternoon|evening)/)).toBeVisible();
		},
		events: {
			async LOADS(scene) {
				await holds.get(scene)?.release();
				await expectRows(scene);
			},
			async FAILS(scene) {
				await holds.get(scene)?.abort(500);
				await expect(scene.page.getByRole("alert")).toBeVisible();
			},
			async RETRY(scene) {
				await holds.get(scene)?.release();
				await scene.page.getByRole("button", { name: "Refresh" }).click();
				await expectRows(scene);
			},
			async PICK_WEEK(scene) {
				await tab(scene, /^This week/).click();
				await expect(scene.page.getByRole("link").filter({ hasText: "Chennai factory licence" })).toHaveCount(0);
			},
			async PICK_OVERDUE(scene) {
				await tab(scene, /^Overdue/).click();
				await expect(scene.page.getByRole("link").filter({ hasText: "Sample GST demand appeal" })).toHaveCount(0);
			},
			async SERVER_DOWN(scene) {
				await scene.page.route("**/api/**", (route) => route.abort("connectionrefused"));
				await scene.page.getByRole("button", { name: "Refresh" }).click();
				await expect(scene.page.getByText("The server is not answering")).toBeVisible();
			},
			async GOES_OFFLINE(scene) {
				await scene.context.setOffline(true);
				await expect(scene.page.getByText("You are offline")).toBeVisible();
			},
		},
	})
);
