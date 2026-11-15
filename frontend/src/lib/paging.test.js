import { describe, expect, it } from "vitest";
import {
	DEFAULT_PAGE_SIZE,
	clampPage,
	pageCount,
	pageNumbers,
	pageOf,
	pageRange,
	rangeLine,
	savePageSize,
	savedPageSize,
} from "./paging";

const store = () => {
	const values = {};
	return {
		getItem: (key) => values[key] ?? null,
		setItem: (key, value) => {
			values[key] = value;
		},
	};
};

describe("paging a list", () => {
	it("says which rows a page shows, of how many", () => {
		expect(rangeLine(2, 20, 154)).toBe("Showing 21–40 of 154");
		expect(rangeLine(8, 20, 154)).toBe("Showing 141–154 of 154");
		expect(rangeLine(1, 20, 12)).toBe("12 records");
		expect(rangeLine(1, 20, 1)).toBe("1 record");
		expect(rangeLine(1, 20, 0)).toBe("No records");
		expect(pageRange(1, 50, 0)).toEqual({ from: 0, to: 0 });
	});

	it("counts pages, at least one", () => {
		expect(pageCount(154, 20)).toBe(8);
		expect(pageCount(100, 50)).toBe(2);
		expect(pageCount(0, 20)).toBe(1);
	});

	it("offers the first, last and nearby pages, with gaps", () => {
		expect(pageNumbers(1, 1)).toEqual([1]);
		expect(pageNumbers(1, 5)).toEqual([1, 2, 3, 4, 5]);
		expect(pageNumbers(6, 20)).toEqual([1, null, 4, 5, 6, 7, 8, null, 20]);
		expect(pageNumbers(20, 20)).toEqual([1, null, 18, 19, 20]);
		expect(pageNumbers(4, 9)).toEqual([1, 2, 3, 4, 5, 6, null, 9]);
	});

	it("cuts one page out of rows loaded whole, and stays within the pages", () => {
		const rows = Array.from({ length: 45 }, (_, index) => index + 1);
		expect(pageOf(rows, 3, 20)).toEqual([41, 42, 43, 44, 45]);
		expect(clampPage(5, 45, 20)).toBe(3);
		expect(clampPage(0, 45, 20)).toBe(1);
	});

	it("remembers each list's page size, and only the sizes offered", () => {
		const storage = store();
		expect(savedPageSize("filings", storage)).toBe(DEFAULT_PAGE_SIZE);
		savePageSize("filings", 50, storage);
		savePageSize("register", 37, storage);
		expect(savedPageSize("filings", storage)).toBe(50);
		expect(savedPageSize("register", storage)).toBe(DEFAULT_PAGE_SIZE);
	});
});
