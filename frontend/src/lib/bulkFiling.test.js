import { describe, expect, it } from "vitest";
import {
	askPlanLine,
	matchFiles,
	nextStep,
	rowMissing,
	rowValues,
	saveLabel,
} from "./bulkFiling";

const PREPARER = { user: "asha@example.com", roles: ["Compliance User"] };
const REVIEWER = { user: "ravi@example.com", roles: ["Compliance User"] };
const MANAGER = { user: "meera@example.com", roles: ["Compliance Manager"] };
const reviewed = { requires_review: 1, requires_proof: 1 };
const row = (fields) => ({
	status: "Open",
	responsible: PREPARER.user,
	reviewer: REVIEWER.user,
	...fields,
});

describe("each row's next step", () => {
	it("sends a reviewed return for review, then lets the reviewer mark it filed", () => {
		expect(nextStep(row({}), reviewed, PREPARER).status).toBe("Ready for Review");
		const waiting = row({ status: "Ready for Review" });
		expect(nextStep(waiting, reviewed, PREPARER)).toEqual({
			status: null,
			label: "With the reviewer",
		});
		expect(nextStep(waiting, reviewed, REVIEWER).status).toBe("Filed");
		expect(nextStep(waiting, reviewed, MANAGER).status).toBe("Filed");
	});

	it("marks a return without review filed, and leaves other people's alone", () => {
		expect(nextStep(row({}), { requires_review: 0 }, PREPARER).status).toBe("Filed");
		const someoneElse = { user: "x@example.com", roles: ["Compliance User"] };
		expect(nextStep(row({}), reviewed, someoneElse)).toEqual({
			status: null,
			label: "Not yours to file",
		});
	});
});

describe("matching dropped proofs to rows", () => {
	const rows = [
		{ name: "CT-1", registration_number: "29ABCDE1234F1Z5", acknowledgement_number: "" },
		{ name: "CT-2", registration_number: "27PQRSX9876K1Z2", acknowledgement_number: "AA2911" },
		{ name: "CT-3", registration_number: "", acknowledgement_number: "" },
	];
	const file = (name) => ({ name });

	it("goes by GSTIN or acknowledgement number in the file name, ignoring case and dashes", () => {
		const { matched, unmatched } = matchFiles(
			[file("gstr3b-29abcde1234f1z5-nov.pdf"), file("ack_AA2911.pdf"), file("scan001.pdf")],
			rows
		);
		expect(matched["CT-1"].name).toBe("gstr3b-29abcde1234f1z5-nov.pdf");
		expect(matched["CT-2"].name).toBe("ack_AA2911.pdf");
		expect(unmatched.map((item) => item.name)).toEqual(["scan001.pdf"]);
	});

	it("leaves a second file for the same row, and short numbers, for choosing by hand", () => {
		const { matched, unmatched } = matchFiles(
			[file("29ABCDE1234F1Z5.pdf"), file("29ABCDE1234F1Z5 (1).pdf")],
			[...rows, { name: "CT-4", registration_number: "", acknowledgement_number: "12" }]
		);
		expect(Object.keys(matched)).toEqual(["CT-1"]);
		expect(unmatched.length).toBe(1);
	});
});

describe("what a row sends", () => {
	it("takes the shared date where the row has none, and amounts only for payments", () => {
		expect(rowValues({ acknowledgement_number: " AA1 " }, "2026-12-18", {})).toEqual({
			filed_on: "2026-12-18",
			acknowledgement_number: "AA1",
		});
		expect(
			rowValues({ filed_on: "2026-12-17", amount_paid: "1200" }, "2026-12-18", {
				requires_payment: 1,
			})
		).toEqual({ filed_on: "2026-12-17", acknowledgement_number: null, amount_paid: 1200 });
	});

	it("says what is still missing, counting a proof waiting to upload", () => {
		expect(rowMissing({}, "2026-12-18", reviewed, false)).toEqual([
			"Acknowledgement number",
			"Proof",
		]);
		expect(rowMissing({ acknowledgement_number: "AA1" }, "", reviewed, true)).toEqual([
			"Filed on",
		]);
	});

	it("words the save button for what is ticked", () => {
		expect(saveLabel(["Ready for Review", "Ready for Review"])).toBe("Send 2 for review");
		expect(saveLabel(["Filed"])).toBe("Mark 1 filed");
		expect(saveLabel(["Filed", "Ready for Review"])).toBe("Save 2");
		expect(saveLabel([])).toBe("Nothing ticked");
	});
});

describe("who asking in bulk reaches", () => {
	it("says how many are asked and why the rest are not", () => {
		expect(askPlanLine({ to_ask: 3, asked_already: 1, no_client: 2 })).toBe(
			"3 companies will be asked; 1 company already has a request open; 2 companies are not linked to a client."
		);
	});
	it("leaves out what does not apply", () => {
		expect(askPlanLine({ to_ask: 1, asked_already: 0, no_client: 0 })).toBe(
			"1 company will be asked."
		);
		expect(askPlanLine({ to_ask: 0, asked_already: 2, no_client: 0 })).toBe(
			"Nobody is left to ask; 2 companies already have a request open."
		);
	});
});
