import { describe, expect, it } from "vitest";
import { LOG_VIEWS, logRow } from "./reminderLog";

describe("the reminder log", () => {
	it("says what each was about, to whom, and opens it", () => {
		const row = logRow({
			name: "x1",
			kind: "Reminder",
			compliance_task: "CT-26-00002",
			sent_to: "asha@example.com\nravi@example.com\nmeera@example.com",
			due_date: "2026-12-20",
			sent_on: "2026-12-13 08:00:00",
		});
		expect(row.title).toBe("Reminder: CT-26-00002");
		expect(row.detail).toMatch(/^asha@example.com, ravi@example.com and 1 more · due /);
		expect(row.to).toEqual({ name: "ComplianceTask", params: { name: "CT-26-00002" } });
		expect(logRow({ name: "x2", kind: "Digest" }).title).toBe("Digest: Weekly summary");
		expect(logRow({ name: "x3", kind: "Escalation", compliance_item: "CI-1" }).theme).toBe(
			"amber"
		);
	});

	it("can be narrowed to one kind", () => {
		expect(LOG_VIEWS.find((view) => view.value === "escalations").filters).toEqual([
			["kind", "=", "Escalation"],
		]);
		expect(LOG_VIEWS[0].filters).toEqual([]);
	});
});
