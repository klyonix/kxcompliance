import { describe, expect, it } from "vitest";
import {
	changeFor,
	controlFor,
	mayChangeField,
	noteText,
	readValue,
	selectOptions,
} from "./editing";

const DATA = { fieldtype: "Data", options: [], reqd: false };
const DATE = { fieldtype: "Date", options: [], reqd: false };
const NOTE = { fieldtype: "Text Editor", options: [], reqd: false };
const ROLE = { fieldtype: "Select", options: ["Petitioner", "Noticee"], reqd: true };
const PERSON = { fieldtype: "Link", options: [], reqd: true };

describe("editing details in place", () => {
	it("gives each kind of field its control", () => {
		expect([DATA, DATE, NOTE, ROLE, PERSON].map(controlFor)).toEqual([
			"text",
			"date",
			"note",
			"select",
			"person",
		]);
	});

	it("reads people by name and notes as plain text", () => {
		expect(readValue(PERSON, "asha@example.com", () => "Asha Rao")).toBe("Asha Rao");
		expect(readValue(NOTE, "<p>Reply filed</p>")).toBe("Reply filed");
		expect(readValue(DATA, "")).toBe("");
	});

	it("keeps a note's paragraphs and line breaks", () => {
		expect(noteText("<p>Reply filed.</p><p>Hearing on 5 Dec.<br>Bring the order.</p>")).toBe(
			"Reply filed.\nHearing on 5 Dec.\nBring the order."
		);
		expect(changeFor(NOTE, "<p>One</p><p>Two</p>", "One\nTwo")).toBeNull();
	});

	it("sends only what changed, trimmed, with notes as paragraphs", () => {
		expect(changeFor(DATA, "ST/42", " ST/42 ")).toBeNull();
		expect(changeFor(DATA, "ST/42", "ST/43")).toBe("ST/43");
		expect(changeFor(DATA, "ST/42", "")).toBe("");
		expect(changeFor(NOTE, "<p>Old</p>", "New\nline")).toBe("<p>New</p><p>line</p>");
		expect(changeFor(NOTE, "<p>Same</p>", "Same")).toBeNull();
		expect(changeFor(DATE, null, "2026-12-01")).toBe("2026-12-01");
	});

	it("lets an optional choice be emptied, not a required one", () => {
		expect(selectOptions(ROLE).map((option) => option.value)).toEqual([
			"Petitioner",
			"Noticee",
		]);
		expect(selectOptions({ ...ROLE, reqd: false })[0].value).toBe("");
	});

	it("leaves reassigning to managers", () => {
		expect(mayChangeField("title", { mayEdit: true, people: [] })).toBe(true);
		expect(mayChangeField("responsible", { mayEdit: true, people: [] })).toBe(false);
		expect(mayChangeField("responsible", { mayEdit: true, people: [{ name: "a" }] })).toBe(
			true
		);
		expect(mayChangeField("title", { mayEdit: false, people: [] })).toBe(false);
	});
});

describe("amounts edited in place", () => {
	const amount = { fieldtype: "Currency" };
	it("reads as a number and sends one only when it changed", () => {
		expect(controlFor(amount)).toBe("number");
		expect(readValue(amount, 250000)).toBe((250000).toLocaleString());
		expect(changeFor(amount, 250000, "250000")).toBeNull();
		expect(changeFor(amount, 250000, "300000")).toBe(300000);
		expect(changeFor(amount, 250000, "")).toBe(0);
	});
});
