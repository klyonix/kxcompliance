import { expect } from "@playwright/test";
import { setup } from "xstate";
import { atBothWidths, defineFlow, type AnyEvent } from "../flow";
import type { Scene } from "../scene";

const COMPANY = "Demo Compliance Pvt Ltd";
const TINY_PNG = Buffer.from(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
	"base64"
);
const today = (days = 0) => {
	const date = new Date();
	date.setDate(date.getDate() + days);
	return date.toISOString().slice(0, 10);
};

async function itemNamed(scene: Scene, title: string): Promise<string> {
	const response = await scene.api.get("/api/v2/document/Compliance%20Item", {
		params: { filters: JSON.stringify([["title", "=", title]]), fields: JSON.stringify(["name"]) },
	});
	return (await response.json()).data[0].name;
}

const button = (scene: Scene, name: string | RegExp) => scene.page.getByRole("button", { name }).first();
const dialog = (scene: Scene) => scene.page.getByRole("dialog");

// ---------------------------------------------------------------------------------------------

/** One register item: its page, and the two dialogs it opens. ComplianceItem.vue. */
const itemMachine = setup({}).createMachine({
	id: "item",
	initial: "page",
	states: {
		page: {
			meta: { description: "An item due for renewal: status and validity, certificate, details and renewals, with Start renewal." },
			on: { START_RENEWAL: "renewalDialog", OPEN_MENU: "menu" },
		},
		renewalDialog: { meta: { description: "Start renewal asks for the stage and the application reference." } },
		menu: {
			meta: { description: "The ⋯ menu: open in the Desk, or cancel the item." },
			on: { CANCEL_ITEM: "cancelDialog" },
		},
		cancelDialog: { meta: { description: "Cancel item asks for a reason, in red." } },
	},
});

export const item = atBothWidths(
	defineFlow<AnyEvent>({
		id: "item",
		title: "Register item",
		source: "frontend/src/pages/ComplianceItem.vue",
		machine: itemMachine,
		async enter(scene) {
			await scene.goto(`/register/${await itemNamed(scene, "Sample pollution consent")}`);
			await expect(scene.page.getByText("Valid until")).toBeVisible();
		},
		events: {
			async START_RENEWAL(scene) {
				await button(scene, "Start renewal").click();
				await expect(dialog(scene).getByText("Application reference")).toBeVisible();
			},
			async OPEN_MENU(scene) {
				await button(scene, "More actions").click();
				await expect(scene.page.getByRole("menuitem", { name: "Cancel item" })).toBeVisible();
			},
			async CANCEL_ITEM(scene) {
				await scene.page.getByRole("menuitem", { name: "Cancel item" }).click();
				await expect(dialog(scene).getByText("Reason").first()).toBeVisible();
			},
		},
	})
);

// ---------------------------------------------------------------------------------------------

async function newTask(scene: Scene, values: Record<string, unknown>): Promise<string> {
	const task = await scene.insert("Compliance Task", {
		obligation_template: "GSTR-3B (Monthly)",
		company: COMPANY,
		period_label: "Oct 2026",
		period_start: "2026-10-01",
		period_end: "2026-10-31",
		due_date: today(6),
		status: "Open",
		responsible: "Administrator",
		...values,
	});
	return task.name as string;
}

async function proofFile(scene: Scene): Promise<string> {
	const response = await scene.api.post("/api/method/upload_file", {
		multipart: {
			file: { name: "gstr3b-oct-ack.png", mimeType: "image/png", buffer: TINY_PNG },
			is_private: "1",
		},
	});
	const file = (await response.json()).message;
	scene.track("File", file.name);
	return file.file_url;
}

/** Filing a return as the person responsible: ComplianceTask.vue with taskActions() deciding the buttons. */
const preparerMachine = setup({}).createMachine({
	id: "filing",
	initial: "open",
	states: {
		open: {
			meta: { description: "An open filing the person holds: the filing form, Save, and Send for review because this return is reviewed." },
			on: { SEND_EMPTY: "missingDetails", FILL: "filled", OPEN_MENU: "menu" },
		},
		missingDetails: { meta: { description: "Send for review with nothing filled: each missing detail is flagged where it is, and named at the foot." } },
		filled: {
			meta: { description: "Filed date, acknowledgement number, proof and amounts filled in, not yet saved." },
			on: { SEND: "sentForReview" },
		},
		sentForReview: { meta: { description: "Sent for review: the form stays editable and says who has to check it next." } },
		menu: { meta: { description: "The ⋯ menu: open in the Desk, or close the filing as not applicable." }, on: { NOT_APPLICABLE: "notApplicableDialog" } },
		notApplicableDialog: { meta: { description: "Does not apply asks why, before the filing is closed for the period." } },
	},
});

export const filing = atBothWidths(
	defineFlow<AnyEvent>({
		id: "filing",
		title: "Filing, as the preparer",
		source: "frontend/src/pages/ComplianceTask.vue, frontend/src/lib/filings.js",
		machine: preparerMachine,
		async enter(scene) {
			await scene.goto(`/filings/${await newTask(scene, {})}`);
			await expect(scene.page.getByRole("heading", { name: "Filing" })).toBeVisible();
		},
		events: {
			async SEND_EMPTY(scene) {
				await button(scene, "Send for review").click();
				await expect(scene.page.getByText(/^Fill in /)).toBeVisible();
			},
			async FILL(scene) {
				const page = scene.page;
				await page.getByPlaceholder("Pick a date").click();
				await page.keyboard.type(today(-1));
				await page.keyboard.press("Enter");
				await page.getByPlaceholder("ARN, challan or SRN").fill("AA2911260012345");
				await page.locator("input[type=file]").setInputFiles({
					name: "gstr3b-oct-ack.png",
					mimeType: "image/png",
					buffer: TINY_PNG,
				});
				await page.getByLabel("Amount paid").fill("184250");
				await page.getByLabel("Remarks").click();
				await expect(page.getByText("Sent with your next save")).toBeVisible();
			},
			async SEND(scene) {
				await button(scene, "Send for review").click();
				await expect(scene.page.getByText(/^Waiting for/)).toBeVisible();
			},
			async OPEN_MENU(scene) {
				await button(scene, "More actions").click();
				await expect(scene.page.getByRole("menuitem", { name: "Does not apply" })).toBeVisible();
			},
			async NOT_APPLICABLE(scene) {
				await scene.page.getByRole("menuitem", { name: "Does not apply" }).click();
				await expect(dialog(scene).getByText("Why it does not apply")).toBeVisible();
			},
		},
	})
);

/** The same page as the reviewer of a filing someone else prepared. */
const reviewerMachine = setup({}).createMachine({
	id: "review",
	initial: "toReview",
	states: {
		toReview: {
			meta: { description: "A filing waiting for this reviewer: Mark filed, Send back and Save, with what to check." },
			on: { SEND_BACK: "sendBackDialog", MARK_FILED: "filed" },
		},
		sendBackDialog: { meta: { description: "Send back asks what needs to change, for the preparer." } },
		filed: { meta: { description: "Marked filed: read-only details, the reviewer recorded, no actions left." } },
	},
});

export const review = atBothWidths(
	defineFlow<AnyEvent>({
		id: "review",
		title: "Filing, as the reviewer",
		source: "frontend/src/pages/ComplianceTask.vue, frontend/src/lib/filings.js",
		machine: reviewerMachine,
		async enter(scene) {
			const name = await newTask(scene, {
				status: "Ready for Review",
				responsible: "asha.rao@example.com",
				reviewer: "Administrator",
				filed_on: today(-1),
				acknowledgement_number: "AA2911260012345",
				proof: await proofFile(scene),
				amount_paid: 184250,
			});
			await scene.goto(`/filings/${name}`);
			await expect(button(scene, "Mark filed")).toBeVisible();
		},
		events: {
			async SEND_BACK(scene) {
				await button(scene, "Send back").click();
				await expect(dialog(scene).getByText("What needs to change").first()).toBeVisible();
			},
			async MARK_FILED(scene) {
				await button(scene, "Mark filed").click();
				await expect(scene.page.getByText("Reviewed by")).toBeVisible();
			},
		},
	})
);

// ---------------------------------------------------------------------------------------------

/** A case logged from a notice, and recording what happened on its date. LegalCase.vue, LegalDates.vue. */
const caseMachine = setup({}).createMachine({
	id: "case",
	initial: "page",
	states: {
		page: {
			meta: { description: "A notice with its amount and risk (shown to managers), the reply date, details and the notice copy." },
			on: { RECORD: "outcomeDialog" },
		},
		outcomeDialog: { meta: { description: "Record outcome: what happened, who attended, proceedings and the next date." }, on: { SAVE_EMPTY: "needsProceedings", SAVE: "recorded" } },
		needsProceedings: { meta: { description: "A hearing marked Done without proceedings: the dialog asks for them." } },
		recorded: { meta: { description: "Outcome saved: the hearing shows Done with the proceedings, Attach order, and the next hearing added." } },
	},
});

export const legalCase = atBothWidths(
	defineFlow<AnyEvent>({
		id: "case",
		title: "Legal case",
		source: "frontend/src/pages/LegalCase.vue, frontend/src/components/LegalRecord.vue, frontend/src/components/LegalDates.vue",
		machine: caseMachine,
		async enter(scene) {
			const legalCase = await scene.insert("Legal Case", {
				title: "GST show cause notice, FY 2024-25",
				case_type: "Tax Notice or Assessment",
				forum: "Tax Officer",
				forum_name: "Assistant Commissioner, Bengaluru South",
				notice_reference: "ZD2911260045",
				filing_date: today(-10),
				company: COMPANY,
				our_role: "Noticee",
				responsible: "Administrator",
				advocate_contact: "Adv. Meera Iyer",
				amount_involved: 1840000,
				provision: 250000,
				risk: "Possible",
			});
			scene.onClose(async () => {
				// Recording an outcome adds the next date; every date must go before the case can.
				const dates = await scene.api.get("/api/v2/document/Legal%20Date", {
					params: { filters: JSON.stringify([["reference_name", "=", legalCase.name]]) },
				});
				for (const { name } of (await dates.json()).data) {
					await scene.page.evaluate(
						(path) => fetch(path, { method: "DELETE", headers: { "X-Frappe-CSRF-Token": (window as { csrf_token?: string }).csrf_token ?? "" } }),
						`/api/v2/document/Legal%20Date/${name}`
					);
				}
			});
			await scene.insert("Legal Date", {
				reference_doctype: "Legal Case",
				reference_name: legalCase.name,
				kind: "Hearing",
				date: today(3),
				purpose: "Personal hearing on the show cause notice",
			});
			await scene.goto(`/legal/case/${legalCase.name}`);
			await expect(button(scene, "Record outcome")).toBeVisible();
		},
		events: {
			async RECORD(scene) {
				await button(scene, "Record outcome").click();
				await expect(dialog(scene).getByText("Proceedings")).toBeVisible();
			},
			async SAVE_EMPTY(scene) {
				await dialog(scene).getByRole("button", { name: "Save outcome" }).click();
				await expect(dialog(scene).getByText("Write what happened at the hearing.")).toBeVisible();
			},
			async SAVE(scene) {
				const box = dialog(scene);
				await box.getByPlaceholder("Advocate or staff").fill("Adv. Meera Iyer");
				await box.getByPlaceholder("What was argued, filed or directed").fill(
					"Reply filed with the reconciliation; the officer asked for invoices for March."
				);
				await box.getByPlaceholder("Select date").click();
				await scene.page.keyboard.type(today(24));
				await scene.page.keyboard.press("Enter");
				await box.getByRole("button", { name: "Save outcome" }).click();
				await expect(scene.page.getByText("Attach order")).toBeVisible();
			},
		},
	})
);

/** A trademark's page, read only for the demo mark. Trademark.vue. */
export const trademark = atBothWidths(
	defineFlow<AnyEvent>({
		id: "trademark",
		title: "Trademark",
		source: "frontend/src/pages/Trademark.vue",
		machine: setup({}).createMachine({
			id: "trademark",
			initial: "page",
			states: {
				page: { meta: { description: "A pending application: classes, the next deadline with Record outcome, and its details." } },
			},
		}),
		async enter(scene) {
			await scene.goto("/legal/trademark/TM-26-00001");
			await expect(scene.page.getByText("Examination Report Reply").first()).toBeVisible();
		},
		events: {},
	})
);

/** Logging a notice that has just arrived. NewNotice.vue. */
const noticeMachine = setup({}).createMachine({
	id: "notice",
	initial: "blank",
	states: {
		blank: { meta: { description: "The form as it opens: tax notice from a tax officer preselected, a camera button for the copy." }, on: { SUBMIT_EMPTY: "missing", FILL: "filled", GOES_OFFLINE: "offline" } },
		missing: { meta: { description: "Log notice with nothing filled: what it is and the reply date are asked for." } },
		filled: { meta: { description: "Filled in with a copy of the notice, ready to log." } },
		offline: { meta: { description: "Offline: the form says logging needs a connection and Log notice is disabled." } },
	},
});

export const notice = atBothWidths(
	defineFlow<AnyEvent>({
		id: "notice",
		title: "Log a notice",
		source: "frontend/src/pages/NewNotice.vue",
		machine: noticeMachine,
		async enter(scene) {
			await scene.goto("/legal/new");
			await expect(scene.page.getByText("Copy of the notice")).toBeVisible();
		},
		events: {
			async SUBMIT_EMPTY(scene) {
				await button(scene, "Log notice").click();
				await expect(scene.page.getByText("Say what the notice is.")).toBeVisible();
			},
			async FILL(scene) {
				const page = scene.page;
				await page.getByPlaceholder("Show cause notice, GST FY 2024-25").fill("Intimation under section 73, FY 2023-24");
				await page.getByPlaceholder("Pick a date").click();
				await page.keyboard.type(today(15));
				await page.keyboard.press("Enter");
				await page.getByPlaceholder("DIN or reference number").fill("ZD2911260078");
				await page.locator("input[type=file]").setInputFiles({ name: "drc-01a.png", mimeType: "image/png", buffer: TINY_PNG });
				await expect(page.getByText("drc-01a.png")).toBeVisible();
			},
			async GOES_OFFLINE(scene) {
				await scene.context.setOffline(true);
				await expect(scene.page.getByText("Logging a notice needs a connection")).toBeVisible();
			},
		},
	})
);
