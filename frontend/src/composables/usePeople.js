// People's names for the user IDs the app shows, fetched once per page load and shared.
import { reactive } from "vue";
import { call } from "@/api";

const names = reactive({});
const asked = new Set();

// The name to show for a user ID: the person's name once known, the ID until then.
export const nameOf = (user) => (user ? names[user] || user : "");

// Fetch the names not yet known; a failure leaves the IDs showing, which still identify people.
export async function learnNames(users) {
	const wanted = [...new Set(users.filter((user) => user && !asked.has(user)))];
	if (!wanted.length) return;
	wanted.forEach((user) => asked.add(user));
	try {
		Object.assign(
			names,
			await call("kxcompliance.api.full_names", { users: wanted.join(",") })
		);
	} catch {
		wanted.forEach((user) => asked.delete(user));
	}
}
