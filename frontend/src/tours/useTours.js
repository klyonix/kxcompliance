// Running a tour: find what each step points at, draw it with driver.js, and tell the server it was
// shown, so a page's tour plays by itself only the first time (RK, 15 Nov 2026).
//
// driver.js, the library Frappe's own Desk tours and KlyONIX One use, is loaded when a tour
// starts rather than with the page, so someone who never sees a tour never downloads it.
import { call } from "@/api";
import { boot, checksOnly, isClientLogin, isManager } from "@/boot";
import { TOURS, tourById, tourFor } from "./tours";

const isFirm = () => boot.accountType === "CA/CS Firm";

// The tours this person may take, by the same rules as the side bar.
export function toursForReader(reader = {}) {
	const client = reader.client ?? isClientLogin();
	const manager = reader.manager ?? isManager();
	const firm = reader.firm ?? isFirm();
	const checks = reader.checks ?? checksOnly();
	return TOURS.filter((tour) => {
		if (client) return Boolean(tour.client);
		if (checks) return ["licence-check", "help"].includes(tour.id);
		if (tour.staff === false) return false;
		if (tour.managers && !manager) return false;
		if (tour.firm && !firm) return false;
		if (
			tour.id === "reminder-log" &&
			!manager &&
			!(reader.auditor ?? boot.roles.includes("Compliance Auditor"))
		)
			return false;
		if (tour.organisation && firm) return false;
		return true;
	});
}

// "section:penalty-heading" is the section that heading labels; any other name is a data-tour marker.
export const selectorOf = (name) =>
	name.startsWith("section:")
		? `[aria-labelledby="${name.slice("section:".length)}"]`
		: `[data-tour="${name}"]`;

// The element a step points at: the first of its targets that is on screen.
export function targetOf(step, root = document) {
	for (const name of step.target || []) {
		for (const element of root.querySelectorAll(selectorOf(name))) {
			// A hidden copy, such as the side bar on a phone, is not somewhere to point.
			if (element.getClientRects().length) return element;
		}
	}
	return null;
}

// The steps this reader will meet: a step with no target is a message in the middle of the screen;
// a step whose target is not drawn for this reader is left out.
export function stepsFor(tour, root = document) {
	const steps = [];
	for (const step of tour.steps) {
		const popover = { title: step.title, description: step.text };
		if (!step.target?.length) steps.push({ popover });
		else {
			const element = targetOf(step, root);
			if (element) steps.push({ element, popover });
		}
	}
	return steps;
}

const WAIT_MS = 2500;
const pointsAtSomething = (tour) => tour.steps.some((step) => step.target && targetOf(step));

// Wait for the page to draw what the tour points at (a list may still be loading), or give up.
async function pageReady(tour) {
	const until = Date.now() + WAIT_MS;
	while (!pointsAtSomething(tour) && Date.now() < until) {
		await new Promise((resolve) => setTimeout(resolve, 100));
	}
}

let seen = null;
let running = false;

// The tours already shown to this person, asked once per visit. A failed read answers "all of
// them", so nothing starts by itself: a tour that plays again because the server did not answer
// is the app nagging, and one that does not play is still one press away.
export function seenTours() {
	if (!seen) {
		seen = call("kxcompliance.api.tours_seen")
			.then((answer) => new Set(answer.seen))
			.catch(() => new Set(TOURS.map((tour) => tour.id)));
	}
	return seen;
}

export function resetTours() {
	seen = null;
	running = false;
}

// Start a tour now; false when there is nothing on this screen for it to show.
export async function startTour(id) {
	const tour = tourById(id);
	if (!tour || running) return false;
	running = true;
	await pageReady(tour);
	const steps = stepsFor(tour);
	if (!steps.some((step) => step.element) && steps.length < 2) {
		running = false;
		return false;
	}
	const [{ driver }] = await Promise.all([
		import("driver.js"),
		import("driver.js/dist/driver.css"),
	]);
	driver({
		steps,
		showProgress: steps.length > 1,
		progressText: "{{current}} of {{total}}",
		nextBtnText: "Next",
		prevBtnText: "Back",
		doneBtnText: "Done",
		popoverClass: "kx-tour",
		overlayOpacity: 0.45,
		stagePadding: 6,
		stageRadius: 8,
		smoothScroll: true,
		onDestroyed: () => {
			running = false;
		},
	}).drive();
	(await seenTours()).add(id);
	// Every start is counted: replays show where people still have doubts.
	call("kxcompliance.api.tour_opened", { tour: id }, { httpMethod: "POST" }).catch(() => {
		// Not remembering it only means it may start by itself once more.
	});
	return true;
}

// This page's tour, the first time this person opens it.
export async function autoStart(route) {
	const tour = tourFor(route);
	if (!tour || running) return false;
	if (!toursForReader().some((allowed) => allowed.id === tour.id)) return false;
	if ((await seenTours()).has(tour.id)) return false;
	return startTour(tour.id);
}
