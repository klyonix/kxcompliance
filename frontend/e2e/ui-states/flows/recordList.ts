import { expect } from "@playwright/test";
import { setup } from "xstate";
import { atBothWidths, defineFlow, type AnyEvent, type AnyFlow } from "../flow";
import type { Hold, Scene } from "../scene";

interface View {
	/** The tab's label, as TabButtons shows it. */
	tab: string;
	state: string;
	description: string;
	/** Text only this tab's list shows. */
	shows: string;
}

interface ListFlow {
	id: string;
	title: string;
	path: string;
	/** The first tab's request, held for the skeleton. */
	request: RegExp;
	/** Text a row of the first tab shows. */
	firstRow: string;
	firstDescription: string;
	views: View[];
}

/**
 * A list screen built on RecordList.vue: skeleton, failed, the first tab's rows, the other
 * tabs, and a search nothing matches. RecordList decides the screen from error, loading,
 * records.length and the current view, read in order.
 */
export function recordListFlow(spec: ListFlow): AnyFlow[] {
	const viewStates = Object.fromEntries(
		spec.views.map((view) => [view.state, { meta: { description: view.description } }])
	);
	const machine = setup({}).createMachine({
		id: spec.id,
		initial: "skeleton",
		states: {
			skeleton: {
				meta: { description: "The list is loading: skeleton rows under the tabs and search." },
				on: { LOADS: "rows", FAILS: "failed" },
			},
			failed: { meta: { description: "Loading the list failed on the server: the message in red, in place of the rows." } },
			rows: {
				meta: { description: spec.firstDescription },
				on: {
					SEARCH_MISS: "searchEmpty",
					...Object.fromEntries(spec.views.map((view) => [`PICK_${view.state.toUpperCase()}`, view.state])),
				},
			},
			searchEmpty: { meta: { description: "A search nothing matches: No matches, and a hint to try another word or tab." } },
			...viewStates,
		},
	});
	const holds = new WeakMap<Scene, Hold>();
	const events: Record<string, (scene: Scene) => Promise<void>> = {
		async LOADS(scene) {
			await holds.get(scene)?.release();
			await expect(scene.page.getByText(spec.firstRow).first()).toBeVisible();
		},
		async FAILS(scene) {
			await holds.get(scene)?.abort(500);
			await expect(scene.page.getByRole("alert")).toBeVisible();
		},
		async SEARCH_MISS(scene) {
			await scene.page.getByRole("searchbox").fill("zxqv");
			await expect(scene.page.getByText("No matches")).toBeVisible();
		},
	};
	for (const view of spec.views) {
		events[`PICK_${view.state.toUpperCase()}`] = async (scene) => {
			await scene.page.getByRole("radio", { name: view.tab }).click();
			await expect(scene.page.getByText(view.shows).first()).toBeVisible();
		};
	}
	return atBothWidths(
		defineFlow<AnyEvent>({
			id: spec.id,
			title: spec.title,
			source: "frontend/src/components/RecordList.vue",
			machine,
			async enter(scene) {
				holds.set(scene, await scene.hold(spec.request));
				await scene.goto(spec.path);
				await expect(scene.page.getByRole("searchbox")).toBeVisible();
			},
			events,
		})
	);
}

export const register = recordListFlow({
	id: "register",
	title: "Register",
	path: "/register",
	request: /\/api\/v2\/document\/Compliance%20Item\?/,
	firstRow: "Sample pollution consent",
	firstDescription: "Needs attention: draft, due, expired, lapsed and in-renewal items, soonest expiry first.",
	views: [
		{ tab: "Active", state: "active", description: "Active items only.", shows: "Sample fire policy" },
		{ tab: "All", state: "all", description: "Every item, cancelled ones included.", shows: "Sample trade licence" },
	],
});

export const filings = recordListFlow({
	id: "filings",
	title: "Filings",
	path: "/filings",
	request: /\/api\/v2\/document\/Compliance%20Task\?/,
	firstRow: "TDS/TCS Payment",
	firstDescription: "To file: open and in-progress filings, soonest due first.",
	views: [
		{ tab: "For review", state: "forReview", description: "Filings sent for review, waiting for a reviewer.", shows: "GSTR-3B (Monthly)" },
		{ tab: "Done", state: "done", description: "Filed and closed filings, latest due first; empty here until something is filed.", shows: "Nothing filed yet" },
	],
});

export const legal = recordListFlow({
	id: "legal",
	title: "Legal",
	path: "/legal",
	request: /\/api\/v2\/document\/Legal%20Date\?/,
	firstRow: "Sample GST demand appeal",
	firstDescription: "Coming up: scheduled hearings, reply dates and trademark deadlines, soonest first, with Log notice in the header.",
	views: [
		{ tab: "Cases", state: "cases", description: "Open cases with their type, forum and next date.", shows: "Commissioner (Appeals)" },
		{ tab: "Trademarks", state: "trademarks", description: "Live trademarks with their next deadline.", shows: "DEMOMARK" },
	],
});
