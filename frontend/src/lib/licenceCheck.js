// Read the licence check answer for the screen, kept apart so it can be tested.
import { formatDate } from "@/lib/format";
import { daysBetween } from "@/pages/myWork";

const SOON_DAYS = 30;
const toDate = (value) => new Date(`${value}T00:00:00`);

// The one-line answer: can the business sell to or buy from this party today?
export function verdict(check) {
	const selling = check.party_type === "Customer";
	const verb = selling ? "Selling to" : "Buying from";
	const failing = check.requirements.filter((row) => row.result !== "ok");
	const blocked = failing.filter((row) => row.action === "Block");
	if (blocked.length) {
		return {
			theme: "red",
			icon: "lucide-octagon-x",
			title: `${verb} ${check.party_name} is blocked`,
			detail: `${
				selling ? "Sales" : "Purchases"
			} of the items a missing licence covers are stopped until a valid one is recorded.`,
		};
	}
	if (failing.length) {
		return {
			theme: "amber",
			icon: "lucide-triangle-alert",
			title: `${verb} ${check.party_name} goes through with a warning`,
			detail: "Each document will say which licence is missing.",
		};
	}
	if (!check.requirements.length) {
		return {
			theme: "gray",
			icon: "lucide-circle-check",
			title: "No licence is required",
			detail: `No licence requirement applies to ${check.party_name}.`,
		};
	}
	return {
		theme: "green",
		icon: "lucide-circle-check",
		title: `${check.party_name} holds every licence needed`,
		detail: "",
	};
}

// What a requirement needs, in words: "Needed for items in Drugs, Vaccines on Sales Order, ..."
export function coverage(requirement) {
	const items = requirement.item_groups.length
		? `items in ${requirement.item_groups.join(", ")}`
		: "every item";
	const documents = requirement.documents.length
		? requirement.documents.join(", ")
		: "no document yet";
	return `Needed for ${items}, on ${documents}`;
}

export function requirementState(requirement) {
	if (requirement.result === "ok") return { label: "In order", theme: "green" };
	const label = requirement.result === "expired" ? "Expired" : "Missing";
	return { label, theme: requirement.action === "Block" ? "red" : "amber" };
}

// How a held licence stands on the day checked.
export function licenceState(licence, checkedOn) {
	const days = licence.valid_until
		? daysBetween(toDate(checkedOn), toDate(licence.valid_until))
		: null;
	if (!licence.valid) {
		return days !== null && days < 0
			? {
					label: "Expired",
					theme: "red",
					detail: `Expired ${formatDate(licence.valid_until)}`,
			  }
			: { label: "Not yet in force", theme: "gray", detail: "" };
	}
	if (days === null) return { label: "Valid", theme: "green", detail: "No expiry" };
	if (days <= SOON_DAYS) {
		return {
			label: "Expires soon",
			theme: "amber",
			detail: days === 0 ? "Expires today" : `Expires in ${days} days`,
		};
	}
	return {
		label: "Valid",
		theme: "green",
		detail: `Valid until ${formatDate(licence.valid_until)}`,
	};
}

// A customer or supplier found by the search, as a row that opens their check.
export function partyRow(result, partyType) {
	return {
		key: result.name,
		kind: partyType === "Supplier" ? "supplier" : "customer",
		title: result.party_name || result.name,
		detail: result.name !== result.party_name ? result.name : "",
		status: "",
		due: { text: "", late: false },
		cells: [result.party_group || ""],
		to: { query: { party_type: partyType, party: result.name } },
	};
}

// A licence the party holds, as a row; it opens its register item for those who may read it.
export function heldRow(licence, checkedOn, { linked = false } = {}) {
	const state = licenceState(licence, checkedOn);
	return {
		key: licence.name || `${licence.item_type}-${licence.reference_number}`,
		kind: "licence",
		title: licence.item_type,
		detail: [licence.reference_number, state.detail].filter(Boolean).join(" · "),
		status: state.label,
		theme: state.theme,
		due: { text: "", late: false },
		to:
			linked && licence.name
				? { name: "ComplianceItem", params: { name: licence.name } }
				: null,
	};
}
