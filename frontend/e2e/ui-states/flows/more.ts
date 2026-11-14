import { expect } from "@playwright/test";
import { setup } from "xstate";
import { atBothWidths, defineFlow, type AnyEvent } from "../flow";
import type { Hold, Scene } from "../scene";

const button = (scene: Scene, name: string | RegExp) => scene.page.getByRole("button", { name }).first();

/** Checking a customer's or supplier's licences. LicenceCheck.vue and lib/licenceCheck.js. */
const checkMachine = setup({}).createMachine({
	id: "licence-check",
	initial: "search",
	states: {
		search: {
			meta: { description: "Customer or Supplier, a search box, and the first customers listed." },
			on: { SEARCH_MISS: "noMatch", OPEN_BLOCKED: "blocked", OPEN_CLEAR: "allClear", PICK_SUPPLIERS: "suppliers" },
		},
		noMatch: { meta: { description: "A search no customer matches." } },
		blocked: { meta: { description: "A customer missing a blocking licence: the red answer, each requirement, and the licences held." } },
		allClear: { meta: { description: "A customer holding every licence needed, one of them expiring within a month." } },
		suppliers: { meta: { description: "The Supplier side of the search." }, on: { OPEN_SUPPLIER: "supplier" } },
		supplier: { meta: { description: "A supplier holding the licence their purchases need." } },
	},
});

const party = (scene: Scene, name: string) => scene.page.getByRole("link").filter({ hasText: name });

export const licenceCheck = atBothWidths(
	defineFlow<AnyEvent>({
		id: "licence-check",
		title: "Licence Check",
		source: "frontend/src/pages/LicenceCheck.vue, frontend/src/lib/licenceCheck.js",
		machine: checkMachine,
		async enter(scene) {
			await scene.goto("/licence-check");
			await expect(party(scene, "Demo City Pharmacy")).toBeVisible();
		},
		events: {
			async SEARCH_MISS(scene) {
				await scene.page.getByRole("searchbox").fill("zxqv");
				await expect(scene.page.getByText(/No customer matches/)).toBeVisible();
			},
			async OPEN_BLOCKED(scene) {
				await party(scene, "Demo Corner Store").click();
				await expect(scene.page.getByText("is blocked")).toBeVisible();
			},
			async OPEN_CLEAR(scene) {
				await party(scene, "Demo City Pharmacy").click();
				await expect(scene.page.getByText("holds every licence needed")).toBeVisible();
			},
			async PICK_SUPPLIERS(scene) {
				await scene.page.getByRole("radio", { name: "Supplier" }).click();
				await expect(party(scene, "Demo Pharma Wholesale")).toBeVisible();
			},
			async OPEN_SUPPLIER(scene) {
				await party(scene, "Demo Pharma Wholesale").click();
				await expect(scene.page.getByText("Licences held")).toBeVisible();
			},
		},
	})
);

/** Someone who sells and has no compliance role: the app is the Licence Check alone. */
export const salesCheck = atBothWidths(
	defineFlow<AnyEvent>({
		id: "sales-check",
		title: "Licence Check for sales staff",
		source: "frontend/src/navigation.js (sections), frontend/src/router.js (beforeEach), compliance_plus/api.py (party_types_to_check)",
		persona: "Sales User",
		machine: setup({}).createMachine({
			id: "sales-check",
			initial: "search",
			states: {
				search: {
					meta: { description: "A Sales User lands on the Licence Check: customers only, and no other section." },
					on: { OPEN_BLOCKED: "blocked", TRY_MY_WORK: "kept" },
				},
				blocked: { meta: { description: "The same answer the compliance team sees for a blocked customer." } },
				kept: { meta: { description: "Opening My Work by its address brings them back to the Licence Check." } },
			},
		}),
		async enter(scene) {
			await scene.goto("/");
			await expect(party(scene, "Demo City Pharmacy")).toBeVisible();
		},
		events: {
			async OPEN_BLOCKED(scene) {
				await party(scene, "Demo Corner Store").click();
				await expect(scene.page.getByText("is blocked")).toBeVisible();
			},
			async TRY_MY_WORK(scene) {
				await scene.goto("/");
				await expect(scene.page).toHaveURL(/licence-check/);
				await expect(party(scene, "Demo City Pharmacy")).toBeVisible();
			},
		},
	})
);

/** The managers' overview. Overview.vue and compliance_plus/compliance_plus/overview.py. */
const overviewHolds = new WeakMap<Scene, Hold>();
export const overview = atBothWidths(
	defineFlow<AnyEvent>({
		id: "overview",
		title: "Overview",
		source: "frontend/src/pages/Overview.vue, compliance_plus/compliance_plus/overview.py",
		machine: setup({}).createMachine({
			id: "overview",
			initial: "skeleton",
			states: {
				skeleton: { meta: { description: "The numbers are loading: a skeleton for the on-time box and the cards." }, on: { LOADS: "numbers", FAILS: "failed" } },
				failed: { meta: { description: "Loading the overview failed on the server." } },
				numbers: { meta: { description: "The on-time rate and the numbers by area; zeros in grey, each opening its Desk list." } },
			},
		}),
		async enter(scene) {
			overviewHolds.set(scene, await scene.hold("**/api/method/compliance_plus.api.overview*"));
			await scene.goto("/overview");
			await expect(scene.page.locator("[aria-busy=true]").first()).toBeVisible();
		},
		events: {
			async LOADS(scene) {
				await overviewHolds.get(scene)?.release();
				await expect(scene.page.getByText("Filed on time")).toBeVisible();
			},
			async FAILS(scene) {
				await overviewHolds.get(scene)?.abort(500);
				await expect(scene.page.getByRole("alert")).toBeVisible();
			},
		},
	})
);

/** The Account page and changes kept on this device. Account.vue, SyncStatus.vue, offline/outbox.js. */
export const account = atBothWidths(
	defineFlow<AnyEvent>({
		id: "account",
		title: "Account",
		source: "frontend/src/pages/Account.vue, frontend/src/offline/outbox.js",
		machine: setup({}).createMachine({
			id: "account",
			initial: "page",
			states: {
				page: { meta: { description: "Name, appearance, changes on this device (all saved), the Desk and Sign out." }, on: { CONFLICT: "needsLook", DARK: "dark" } },
				needsLook: { meta: { description: "A change made offline that someone else's edit overtook: its error, Send again and Discard, and the red banner." } },
				dark: { meta: { description: "The app in dark appearance." } },
			},
		}),
		async enter(scene) {
			await scene.goto("/account");
			await expect(scene.page.getByText("Changes on this device")).toBeVisible();
		},
		events: {
			async CONFLICT(scene) {
				await scene.page.evaluate(
					() =>
						new Promise<void>((resolve, reject) => {
							const request = indexedDB.open("compliance-plus", 1);
							request.onsuccess = () => {
								const store = request.result.transaction("outbox", "readwrite").objectStore("outbox");
								store.add({
									doctype: "Compliance Task",
									name: "CT-26-00002",
									values: { remarks: "Filed through the GST portal." },
									baseModified: "2026-11-01 10:00:00",
									files: [],
									status: "conflict",
									error: "Compliance Task CT-26-00002 was changed by someone else after this change was made.",
									createdAt: Date.now(),
								}).onsuccess = () => resolve();
							};
							request.onerror = () => reject(request.error);
						})
				);
				await scene.page.reload();
				await expect(button(scene, "Send again")).toBeVisible();
			},
			async DARK(scene) {
				await scene.page.getByRole("radio", { name: "Dark" }).click();
				await expect(scene.page.locator("html")).toHaveAttribute("data-theme", "dark");
			},
		},
	})
);

/** My Work for someone who holds nothing yet. */
export const myWorkEmpty = atBothWidths(
	defineFlow<AnyEvent>({
		id: "my-work-empty",
		title: "My Work, nothing assigned",
		source: "frontend/src/pages/MyWork.vue",
		persona: "Compliance User",
		machine: setup({}).createMachine({
			id: "my-work-empty",
			initial: "empty",
			states: {
				empty: { meta: { description: "A Compliance User with nothing assigned: the empty state, and no Overview." } },
			},
		}),
		async enter(scene) {
			await scene.goto("/");
			await expect(scene.page.getByText("Nothing needs you right now")).toBeVisible();
		},
		events: {},
	})
);
