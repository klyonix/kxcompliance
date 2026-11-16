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

// The app's three roles, as the People screens offer them; only a firm has clients to set up.
export function roleChoices(firm) {
	return [
		{
			label: "Manager",
			detail: firm
				? "Sets up companies, clients and settings, and approves filings."
				: "Sets up companies and settings, and approves filings.",
		},
		{ label: "Staff", detail: "Prepares filings, keeps the register and handles legal work." },
		{ label: "Auditor", detail: "Can read everything and change nothing." },
	];
}

// The signed-in person's role, as the profile popup names it.
export function roleLabel(roles) {
	if (roles.includes("Compliance Manager")) return "Manager";
	if (roles.includes("Compliance User")) return "Staff";
	if (roles.includes("Compliance Auditor")) return "Auditor";
	if (roles.includes("System Manager")) return "Administrator";
	if (roles.includes("Compliance Client")) return "Client";
	return "Licence checks";
}

// What switching someone's sign-in off or back on says, before and after. Nobody is deleted: the
// records they worked on keep their name.
export function switchWords(person, on) {
	const name = person.full_name;
	return on
		? {
				title: "Switch on",
				message: `${name} can sign in again, with the role they had.`,
				confirmLabel: "Switch on",
				done: `${name} can sign in again`,
		  }
		: {
				title: "Switch off",
				message: `${name} can no longer sign in. Their role, the records they worked on and their history stay; switch them on again any time. Hand over any open work they hold, so it does not wait for them.`,
				confirmLabel: "Switch off",
				done: `${name} is switched off`,
		  };
}

// An example address for the invitation, at the firm or the company.
export const inviteEmailHint = (firm) => (firm ? "neha@yourfirm.in" : "neha@yourcompany.in");

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
		// Their photo, or their initials, in place of the row's icon.
		avatar: { image: person.user_image || "", label: person.full_name },
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
