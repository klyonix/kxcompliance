// My Work, loaded once and shared, so the side bar's count and the page agree.
import { computed, reactive } from "vue";
import { call } from "@/api";
import { summarise, workRows } from "@/pages/myWork";
import { notLoaded } from "@/offline/reachability";

export const work = reactive({ data: null, loading: false, error: "" });

export const rows = computed(() => (work.data ? workRows(work.data) : []));
export const counts = computed(() => summarise(rows.value));

export async function loadWork() {
	work.loading = true;
	work.error = "";
	try {
		work.data = await call("compliance_plus.api.my_work");
	} catch (error) {
		// With My Work already on screen, the banner says the server is not answering.
		if (error.isNetwork && work.data) return;
		work.error = error.isNetwork ? notLoaded("My Work") : error.message;
	} finally {
		work.loading = false;
	}
}
