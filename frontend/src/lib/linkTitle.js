// A record's title for showing a link to it, such as a client's name for its ID. Frappe answers
// with the title for doctypes that show titles in links, and with the ID itself otherwise.
import { ref, watch } from "vue";
import { call } from "@/api";

const known = new Map();

export function linkTitle(doctype, name) {
	if (!name) return Promise.resolve("");
	const key = `${doctype}::${name}`;
	if (!known.has(key)) {
		known.set(
			key,
			call("frappe.desk.search.get_link_title", { doctype, docname: name }).catch(() => name)
		);
	}
	return known.get(key);
}

// The title of whichever record `source` names, kept up to date; the ID until it is read.
export function useLinkTitle(doctype, source) {
	const title = ref("");
	watch(
		source,
		async (name) => {
			title.value = name || "";
			const found = await linkTitle(doctype, name);
			if (source() === name) title.value = found || name || "";
		},
		{ immediate: true }
	);
	return title;
}
