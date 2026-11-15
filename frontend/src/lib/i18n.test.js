import { afterEach, describe, expect, it } from "vitest";
import { language, setLanguage, t } from "./i18n";

afterEach(() => setLanguage("en"));

describe("the app's words", () => {
	it("are English unless Hindi is chosen, and fall back to English when untranslated", () => {
		expect(t("Filings")).toBe("Filings");
		setLanguage("hi");
		expect(language()).toBe("hi");
		expect(t("Filings")).toBe("फ़ाइलिंग");
		expect(t("A phrase nobody translated")).toBe("A phrase nobody translated");
	});

	it("fill in their numbers", () => {
		setLanguage("hi");
		expect(t("{0} days late", 5)).toBe("5 दिन देर से");
		expect(t("Back to {0}", t("Filings"))).toBe("फ़ाइलिंग पर वापस");
	});

	it("take only languages they know", () => {
		setLanguage("fr");
		expect(language()).toBe("en");
	});
});
