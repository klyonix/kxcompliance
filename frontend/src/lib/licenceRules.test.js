import { describe, expect, it } from "vitest";
import { checkRow, ruleRow } from "./licenceRules";

describe("licence rules", () => {
	const documents = [
		{ doctype: "Sales Order", field: "check_sales_order", party_type: "Customer" },
		{ doctype: "Sales Invoice", field: "check_sales_invoice", party_type: "Customer" },
	];
	const rule = {
		name: "LR-0001",
		item_type: "Drug Licence",
		party_type: "Customer",
		action: "Block",
		is_active: 1,
		check_sales_order: 1,
	};

	it("lists a rule with what it does and where", () => {
		const row = ruleRow(rule, documents);
		expect(row.status).toBe("Block");
		expect(row.theme).toBe("red");
		expect(row.detail).toBe("Customers need it · blocks Sales Order");
		expect(ruleRow({ ...rule, is_active: 0 }, documents).status).toBe("Off");
		expect(ruleRow({ ...rule, action: "Warn" }, documents).theme).toBe("amber");
	});

	it("lists a checked document, opening it in the Desk", () => {
		const log = {
			name: "LCL-1",
			result: "Blocked",
			reference_doctype: "Sales Order",
			reference_name: "SO-0007",
			party: "City Pharmacy",
			item_type: "Drug Licence",
			message: "",
		};
		const row = checkRow(log, { allowed: false, checkedBy: "Asha Rao" });
		expect(row.status).toBe("Blocked");
		expect(row.cells).toEqual(["City Pharmacy", "Asha Rao"]);
		expect(row.href).toBe("/desk/sales-order/SO-0007");
		expect(checkRow(log, { allowed: true, checkedBy: "" }).status).toBe("Let through");
	});
});
