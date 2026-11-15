// Views of a list: the ones people save (Compliance List View: their own, or shared by a
// manager) and each person's last state on this device, so a list opens as they left it.
import { createDoc, deleteDoc, getList, updateDoc } from "@/api";

const DOCTYPE = "Compliance List View";
export const LAYOUTS = [
	{ value: "list", label: "List", icon: "lucide-list" },
	{ value: "table", label: "Table", icon: "lucide-table-2" },
	{ value: "kanban", label: "Kanban", icon: "lucide-square-kanban" },
];
const LAYOUT_NAMES = { list: "List", table: "Table", kanban: "Kanban" };
const LAYOUT_VALUES = { List: "list", Table: "table", Kanban: "kanban" };

const parse = (text, fallback) => {
	if (!text) return fallback;
	if (typeof text !== "string") return text;
	try {
		return JSON.parse(text);
	} catch {
		return fallback;
	}
};

// Pinned first, then shared, then one's own, each by name.
export function sortViews(views, user) {
	const rank = (view) => (view.is_pinned ? 0 : view.is_shared && view.owner !== user ? 1 : 2);
	return [...views].sort((a, b) => rank(a) - rank(b) || a.label.localeCompare(b.label));
}

export async function loadViews(listKey, user) {
	const { rows } = await getList(DOCTYPE, {
		fields: [
			"name",
			"label",
			"owner",
			"layout",
			"board",
			"base_view",
			"is_shared",
			"is_pinned",
			"filters",
			"order_by",
			"columns",
			"quick_filters",
		],
		filters: [["list_key", "=", listKey]],
		orderBy: "label asc",
		limit: 100,
	});
	return sortViews(rows, user);
}

// A saved view as the list uses it.
export function viewState(view) {
	const snapshot = {};
	const filters = parse(view.filters, null);
	const columns = parse(view.columns, null);
	const quick = parse(view.quick_filters, null);
	const sort = parse(view.order_by, null);
	if (Array.isArray(filters)) snapshot.filters = filters;
	if (Array.isArray(columns) && columns.length) snapshot.columns = columns;
	if (Array.isArray(quick)) snapshot.quickFilterFields = quick;
	if (Array.isArray(sort)) snapshot.sort = sort;
	return {
		layout: LAYOUT_VALUES[view.layout] || "list",
		board: view.board || "",
		baseView: view.base_view || "",
		snapshot,
	};
}

// The record that keeps a view. The sort is kept as the controls hold it, so it comes back as is.
export function viewRecord({ label, listKey, layout, board, baseView, snapshot, shared, pinned }) {
	return {
		label,
		list_key: listKey,
		layout: LAYOUT_NAMES[layout] || "List",
		board: layout === "kanban" ? board : "",
		base_view: baseView,
		filters: JSON.stringify(snapshot?.filters || []),
		order_by: JSON.stringify(snapshot?.sort || []),
		columns: JSON.stringify(snapshot?.columns || []),
		quick_filters: JSON.stringify(snapshot?.quickFilterFields || []),
		is_shared: shared ? 1 : 0,
		is_pinned: pinned ? 1 : 0,
	};
}

export const saveView = (record, name) =>
	name ? updateDoc(DOCTYPE, name, record) : createDoc(DOCTYPE, record);
export const removeView = (name) => deleteDoc(DOCTYPE, name);

// The last state of a list on this device.
// "list2": lists moved to one line of filters (Nov 2026), so what a device remembered from the
// old layout, with every quick filter shown, is left behind.
const lastKey = (listKey) => `kxcompliance:list2:${listKey}`;

export function readLast(listKey, storage = localStorage) {
	const saved = parse(storage.getItem(lastKey(listKey)), null);
	if (!saved || typeof saved !== "object") return null;
	return {
		layout: LAYOUT_VALUES[LAYOUT_NAMES[saved.layout]] ? saved.layout : "list",
		board: typeof saved.board === "string" ? saved.board : "",
		snapshot: saved.snapshot && typeof saved.snapshot === "object" ? saved.snapshot : null,
	};
}

export function writeLast(listKey, state, storage = localStorage) {
	storage.setItem(lastKey(listKey), JSON.stringify(state));
}
