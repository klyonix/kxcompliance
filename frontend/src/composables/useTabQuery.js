// The open tab of a page, kept in the address (?tab=) so a reload or a shared link opens it.
import { ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

export function useTabQuery(values, fallback = values[0]) {
	const route = useRoute();
	const router = useRouter();
	const tab = ref(values.includes(route.query.tab) ? route.query.tab : fallback);
	watch(tab, (value) => {
		const query = { ...route.query, tab: value === fallback ? undefined : value };
		router.replace({ query });
	});
	return tab;
}
