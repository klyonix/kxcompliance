// Signatories (directors, partners, authorised signatories): how they show in lists.

export const DESIGNATIONS = [
	"Director",
	"Managing Director",
	"Whole-time Director",
	"Independent Director",
	"Designated Partner",
	"Partner",
	"Proprietor",
	"Karta",
	"Trustee",
	"Company Secretary",
	"Authorised Signatory",
	"Other",
];

export const SIGNATORY_FIELDS = [
	"name",
	"full_name",
	"designation",
	"company",
	"din",
	"is_active",
];

// The signatories list's columns, boards and filters (RecordList).
export const SIGNATORY_LIST = {
	columns: [
		{ label: "Company", field: "company" },
		{ label: "Designation", field: "designation" },
	],
	dateLabel: "",
};

export const SIGNATORY_VIEWS = [
	{
		label: "Active",
		value: "active",
		filters: [["is_active", "=", 1]],
		orderBy: "full_name asc",
	},
	{
		label: "Former",
		value: "former",
		filters: [["is_active", "=", 0]],
		orderBy: "full_name asc",
	},
];

export function signatoryRow(signatory) {
	return {
		key: signatory.name,
		kind: "signatory",
		title: signatory.full_name,
		detail: [signatory.designation, signatory.company, signatory.din && `DIN ${signatory.din}`]
			.filter(Boolean)
			.join(" · "),
		status: signatory.is_active ? "Active" : "Former",
		theme: signatory.is_active ? "green" : "gray",
		due: { text: "", late: false },
		to: { name: "Signatory", params: { name: signatory.name } },
	};
}
