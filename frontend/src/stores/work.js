// My Work, loaded once and shared, so the side bar's count and the page agree.
import { computed, reactive } from "vue";
import { call } from "@/api";
import { deskRoute } from "@/navigation";
import { summarise, workRows } from "@/pages/myWork";

export const work = reactive({ data: null, loading: false, error: "" });

export const rows = computed(() => (work.data ? workRows(work.data, { link: deskRoute }) : []));
export const counts = computed(() => summarise(rows.value));

export async function loadWork() {
	work.loading = true;
	work.error = "";
	try {
		work.data = await call("compliance_plus.api.my_work");
	} catch (error) {
		work.error = error.isNetwork
			? "You are offline, and My Work has not been loaded on this device yet."
			: error.message;
	} finally {
		work.loading = false;
	}
}
