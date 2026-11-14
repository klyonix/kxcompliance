import { describe, expect, it } from "vitest";
import { onboardingSteps, registrationProblem, setupAnswers, stateFromGstin } from "./onboarding";

const STATES = ["GST", "GST Composition", "LWF", "PT"];
const row = (registration_type, registration_number = "", state = "") => ({
	registration_type,
	registration_number,
	state,
});

describe("onboarding", () => {
	it("asks a firm for its name before the first client's company", () => {
		expect(onboardingSteps("Organisation")).toEqual([
			"who",
			"company",
			"registrations",
			"people",
		]);
		expect(onboardingSteps("CA/CS Firm")).toEqual([
			"who",
			"firm",
			"company",
			"registrations",
			"people",
		]);
	});

	it("ignores blank registrations and names what a started one is missing", () => {
		expect(registrationProblem([row(""), row("TAN", "BLRA12345B")], STATES)).toBe("");
		expect(registrationProblem([row("GST", "29ABCDE1234F1Z5")], STATES)).toMatch(
			/choose the state/
		);
		expect(registrationProblem([row("TAN")], STATES)).toMatch(/enter its number/);
		expect(registrationProblem([row("", "X1")], STATES)).toMatch(/choose which registration/);
	});

	it("sends only the fields the server takes, for the company chosen", () => {
		const setup = setupAnswers(
			{
				account_type: "Organisation",
				firm_name: "Ignored",
				new_company: " Sunrise Foods Private Limited ",
				company: "Old Co",
				company_type: "Private Limited",
				registrations: [row("GST", " 29ABCDE1234F1Z5 ", "Karnataka"), row("")],
				responsible: "asha.rao@example.com",
				reviewer: "",
			},
			"new"
		);
		expect(setup).toEqual({
			account_type: "Organisation",
			firm_name: "",
			new_company: "Sunrise Foods Private Limited",
			company: "",
			company_type: "Private Limited",
			registrations: [
				{
					registration_type: "GST",
					registration_number: "29ABCDE1234F1Z5",
					state: "Karnataka",
				},
			],
			responsible: "asha.rao@example.com",
			reviewer: "",
		});
	});

	it("reads the state from a GSTIN's first two digits", () => {
		expect(stateFromGstin("29AAKCS1234F1Z5")).toBe("Karnataka");
		expect(stateFromGstin(" 27ABCDE1234F1Z5")).toBe("Maharashtra");
		expect(stateFromGstin("9")).toBe("");
	});
});
