// Editing a record's details where they are shown: which control each kind of field gets, how a
// value reads, and what is sent back. The server (kxcompliance.api.editable_fields) says which
// fields the app may change and their kinds; a page lists the details it shows, in order.
import { formatDate } from "@/lib/format";
import { plainText } from "@/lib/legal";
import { commentHtml } from "@/lib/records";

// A note's text with its paragraphs and line breaks kept, one per line.
export function noteText(html) {
	if (!html) return "";
	const lines = String(html)
		.replace(/<br\s*\/?>/gi, "\n")
		.replace(/<\/(p|div|li|h[1-6])>/gi, "\n");
	return plainText(lines)
		.replace(/\n{3,}/g, "\n\n")
		.trim();
}

export const PEOPLE_FIELDS = ["responsible", "reviewer"];

// The control for a field's kind: text, date, select, person or note.
export function controlFor(meta) {
	if (!meta) return null;
	if (meta.fieldtype === "Date") return "date";
	if (meta.fieldtype === "Select") return "select";
	if (meta.fieldtype === "Link") return "person";
	if (meta.fieldtype === "Text Editor") return "note";
	return "text";
}

// How a value reads on the page; `nameOf` turns a user into their name.
export function readValue(meta, value, nameOf = (user) => user) {
	if (!value) return "";
	const control = controlFor(meta);
	if (control === "date") return formatDate(value);
	if (control === "person") return nameOf(value);
	if (control === "note") return noteText(value);
	return String(value);
}

// The value to edit, from what the record holds.
export const editValue = (meta, value) =>
	controlFor(meta) === "note" ? noteText(value) : value || "";

// What goes back to the server for what was typed or chosen; null when nothing changed.
export function changeFor(meta, before, typed) {
	const control = controlFor(meta);
	const value =
		control === "text" || control === "note" ? String(typed || "").trim() : typed || "";
	if (control === "note") {
		return value === noteText(before) ? null : value ? commentHtml(value) : "";
	}
	return value === (before || "") ? null : value;
}

// A select's choices: an optional field may also be left empty.
export const selectOptions = (meta) => [
	...(meta.reqd ? [] : [{ label: "—", value: "" }]),
	...meta.options.map((option) => ({ label: option, value: option })),
];

// Whether a person may change this field: a manager alone reassigns (the server says so too, and
// offers managers the people to choose from).
export function mayChangeField(fieldname, { mayEdit, people }) {
	if (!mayEdit) return false;
	return PEOPLE_FIELDS.includes(fieldname) ? people.length > 0 : true;
}
