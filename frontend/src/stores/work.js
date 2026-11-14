// My Work, loaded once and shared, so the side bar's count and the page agree.
import { computed, reactive } from "vue";
import { call } from "@/api";
import { keepClientWork } from "@/lib/clientFilter";
import { summarise, workRows } from "@/pages/myWork";
import { chosenCompanies } from "@/stores/clientFilter";
import { notLoaded } from "@/offline/reachability";

export const work = reactive({ data: null, loading: false, error: "" });

// Kept to the client chosen on the lists, if any, so the side bar's count matches the page.
export const rows = computed(() =>
	work.data ? workRows(keepClientWork(work.data, chosenCompanies.value)) : []
);
export const counts = computed(() => summarise(rows.value));

export async function loadWork() {
	work.loading = true;
	work.error = "";
	try {
		work.data = await call("kxcompliance.api.my_work");
	} catch (error) {
		// With My Work already on screen, the banner says the server is not answering.
		if (error.isNetwork && work.data) return;
		work.error = error.isNetwork ? notLoaded("My Work") : error.message;
	} finally {
		work.loading = false;
	}
}
