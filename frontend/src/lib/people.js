import { formatDate } from "@/lib/format";

// People offered in a form: by name, with the email added where two people share a name.
export function personOptions(people) {
	const counts = {};
	for (const person of people) {
		const name = person.full_name || person.name;
		counts[name] = (counts[name] || 0) + 1;
	}
	return people.map((person) => {
		const name = person.full_name || person.name;
		return {
			label: counts[name] > 1 && name !== person.name ? `${name} (${person.name})` : name,
			value: person.name,
		};
	});
}

// The app's three roles, as the People screens offer them.
export const ROLES = [
	{ label: "Manager", detail: "Sets up companies, clients and settings, and approves filings." },
	{ label: "Staff", detail: "Prepares filings, keeps the register and handles legal work." },
	{ label: "Auditor", detail: "Can read everything and change nothing." },
];

// One person on the People page (RowList); their role and actions sit beside the row, and the
// row opens their page.
export function personRow(person) {
	let status = "Active";
	let theme = "green";
	if (!person.enabled) [status, theme] = ["Switched off", "gray"];
	else if (!person.last_login) [status, theme] = ["Not signed in yet", "amber"];
	return {
		key: person.user,
		kind: "person",
		title: person.is_me ? `${person.full_name} (you)` : person.full_name,
		detail: person.user,
		status,
		theme,
		due: { text: "", late: false },
		cells: [person.last_login ? formatDate(person.last_login) : ""],
		to: { name: "Person", params: { user: person.user } },
		person,
	};
}

// The people a filter keeps: those whose name or email has the text, in the role chosen ("" any).
export function filterPeople(people, { text = "", role = "" } = {}) {
	const words = text.trim().toLowerCase();
	return people.filter(
		(person) =>
			(!role || person.role === role) &&
			(!words || `${person.full_name} ${person.user}`.toLowerCase().includes(words))
	);
}
