// Rules for showing a Compliance Item, kept apart from the screens so they can be tested.
import { relativeDue } from "@/pages/myWork";

export const ATTENTION_STATUSES = [
	"Draft",
	"Due for Renewal",
	"Expired",
	"Lapsed",
	"Renewal in Progress",
];
export const OPEN_RENEWAL_STATUSES = ["Planned", "Applied"];
export const DSC_TYPE = "Digital Signature Certificate";
export const CUSTODY_STATES = ["With the Firm", "With the Client", "With the Holder", "Not Known"];

export const REGISTER_VIEWS = [
	{
		label: "Needs attention",
		value: "attention",
		filters: [["status", "in", ATTENTION_STATUSES]],
		orderBy: "valid_until asc",
	},
	{
		label: "Active",
		value: "active",
		filters: [["status", "=", "Active"]],
		orderBy: "valid_until asc",
	},
	{
		label: "Digital signatures",
		value: "dsc",
		filters: [
			["item_type", "=", DSC_TYPE],
			["is_cancelled", "=", 0],
		],
		orderBy: "valid_until asc",
	},
	{ label: "All", value: "all", filters: [], orderBy: "valid_until asc" },
];

export const ITEM_LIST_FIELDS = [
	"name",
	"title",
	"item_type",
	"status",
	"valid_until",
	"reference_number",
	"responsible",
	"reviewer",
	"holder_name",
	"custody",
];

export function itemTheme(status) {
	if (["Expired", "Lapsed"].includes(status)) return "red";
	if (["Due for Renewal", "Draft"].includes(status)) return "amber";
	if (status === "Renewal in Progress") return "blue";
	if (status === "Active") return "green";
	return "gray";
}

function dueFor(item, midnight, overdue) {
	if (item.status === "Cancelled") return { text: "", late: false };
	if (!item.valid_until) return { text: "No expiry", late: false };
	return relativeDue(item.valid_until, midnight, { overdue });
}

// A DSC is told apart by whose it is and who has the token; other items by type and number.
function itemDetail(item) {
	if (item.item_type === DSC_TYPE && item.holder_name) {
		const custody = item.custody ? `Token ${item.custody.toLowerCase()}` : "";
		return [item.holder_name, custody || item.company].filter(Boolean).join(" · ");
	}
	return [item.item_type, item.reference_number].filter(Boolean).join(" · ");
}

export function itemRow(item, today = new Date()) {
	const midnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());
	const overdue = ["Expired", "Lapsed"].includes(item.status);
	return {
		key: item.name,
		kind: "licence",
		title: item.title,
		detail: itemDetail(item),
		status: item.status,
		theme: itemTheme(item.status),
		due: dueFor(item, midnight, overdue),
		to: { name: "ComplianceItem", params: { name: item.name } },
	};
}

// Who may act on an item in the app: the same rule the server applies.
export function canAct(item, { user, roles }) {
	if (!item || item.is_cancelled) return false;
	if (roles.includes("Compliance Manager") || roles.includes("System Manager")) return true;
	return [item.responsible, item.reviewer].includes(user);
}

export const searchFilter = (text, field = "title") =>
	text.trim() ? [[field, "like", `%${text.trim()}%`]] : [];
