// The open tab of a page, kept in the address (?tab=, or another key for a second set of tabs) so
// a reload or a shared link opens it.
import { ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

export function useTabQuery(values, fallback = values[0], key = "tab") {
	const route = useRoute();
	const router = useRouter();
	const tab = ref(values.includes(route.query[key]) ? route.query[key] : fallback);
	watch(tab, (value) => {
		const query = { ...route.query, [key]: value === fallback ? undefined : value };
		router.replace({ query });
	});
	return tab;
}
