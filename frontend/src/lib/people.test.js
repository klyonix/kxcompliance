import { describe, expect, it } from "vitest";
import {
	filterPeople,
	inviteEmailHint,
	personOptions,
	personRow,
	roleChoices,
	switchWords,
} from "./people";

describe("personOptions", () => {
	it("names people, and adds the email only where names repeat", () => {
		expect(
			personOptions([
				{ name: "Administrator", full_name: "Administrator" },
				{ name: "admin@example.com", full_name: "Administrator" },
				{ name: "asha@example.com", full_name: "Asha Rao" },
				{ name: "nobody@example.com", full_name: "" },
			]).map((option) => option.label)
		).toEqual([
			"Administrator",
			"Administrator (admin@example.com)",
			"Asha Rao",
			"nobody@example.com",
		]);
	});
});

describe("personRow", () => {
	const person = {
		user: "neha@example.com",
		full_name: "Neha Joshi",
		enabled: 1,
		last_login: "2026-11-14 10:00:00",
	};

	it("says whether someone uses the app", () => {
		expect(personRow(person).status).toBe("Active");
		expect(personRow({ ...person, last_login: null }).status).toBe("Not signed in yet");
		expect(personRow({ ...person, enabled: 0 }).status).toBe("Switched off");
	});

	it("marks the person looking", () => {
		expect(personRow({ ...person, is_me: true }).title).toBe("Neha Joshi (you)");
	});
});

describe("filtering people", () => {
	const people = [
		{ full_name: "Asha Rao", user: "asha@firm.example.com", role: "Manager" },
		{ full_name: "Ravi K", user: "ravi@firm.example.com", role: "Staff" },
	];

	it("keeps a role, and names or emails with the text", () => {
		expect(filterPeople(people, { role: "Staff" }).map((p) => p.full_name)).toEqual([
			"Ravi K",
		]);
		expect(filterPeople(people, { text: "ASHA" }).map((p) => p.full_name)).toEqual([
			"Asha Rao",
		]);
		expect(filterPeople(people, { text: "firm.example" })).toHaveLength(2);
		expect(filterPeople(people)).toHaveLength(2);
	});

	it("speaks of clients only on a firm's site", () => {
		expect(roleChoices(true)[0].detail).toContain("clients");
		expect(roleChoices(false)[0].detail).not.toContain("clients");
		expect(inviteEmailHint(false)).toBe("neha@yourcompany.in");
	});
});

describe("switchWords", () => {
	it("says what switching off keeps, and that switching on restores the role", () => {
		const off = switchWords({ full_name: "Neha Joshi" }, false);
		expect(off.confirmLabel).toBe("Switch off");
		expect(off.message).toContain(
			"Their role, the records they worked on and their history stay"
		);
		const on = switchWords({ full_name: "Neha Joshi" }, true);
		expect([on.confirmLabel, on.done]).toEqual(["Switch on", "Neha Joshi can sign in again"]);
	});
});
