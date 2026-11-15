import { afterEach, describe, expect, it } from "vitest";
import { boot } from "@/boot";
import { formatDate, pickerFormat } from "./format";

describe("dates in the app", () => {
	afterEach(() => {
		boot.dateFormat = "";
	});

	it("follows the site's day-first setting", () => {
		boot.dateFormat = "dd-mm-yyyy";
		expect(formatDate("2026-11-13")).toBe("13 Nov 2026");
		expect(formatDate("2026-11-13", { year: false })).toBe("13 Nov");
		expect(pickerFormat()).toBe("DD-MM-YYYY");
	});

	it("follows a month-first setting", () => {
		boot.dateFormat = "mm-dd-yyyy";
		expect(formatDate("2026-11-13")).toBe("Nov 13, 2026");
		expect(pickerFormat()).toBe("MM-DD-YYYY");
	});

	it("lets a date field take a date typed in the site's own format", () => {
		boot.dateFormat = "dd/mm/yyyy";
		expect(pickerFormat()).toBe("DD/MM/YYYY");
		boot.dateFormat = "";
		expect(pickerFormat()).toBe("DD-MM-YYYY");
	});

	it("shows nothing for no date", () => {
		expect(formatDate(null)).toBe("");
	});
});
