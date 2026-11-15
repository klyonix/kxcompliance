import { describe, expect, it } from "vitest";
import { columnTrack, tableMinWidth } from "./table";

describe("table columns", () => {
	it("keep a chosen width, and share the rest with the name taking twice as much", () => {
		expect(columnTrack({ fieldname: "title" }, 0)).toBe("minmax(14rem, 2fr)");
		expect(columnTrack({ fieldname: "status" }, 1)).toBe("minmax(9rem, 1fr)");
		expect(columnTrack({ fieldname: "status", width: 160 }, 1)).toBe("160px");
	});

	it("scroll sideways once they need more room than the page", () => {
		expect(
			tableMinWidth([
				{ fieldname: "title" },
				{ fieldname: "status" },
				{ fieldname: "x", width: 160 },
			])
		).toBe(33);
	});
});
