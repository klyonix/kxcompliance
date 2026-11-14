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
