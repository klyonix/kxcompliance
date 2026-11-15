<template>
	<RecordList
		title="Obligation library"
		list-key="obligations"
		doctype="Compliance Obligation Template"
		:fields="OBLIGATION_FIELDS"
		:views="views"
		:to-row="obligationRow"
		v-bind="OBLIGATION_LIST"
		search-field="name"
		search-placeholder="Search by name or form"
		:by-client="false"
		:empty="empty"
		:parent="{ label: 'Settings', route: { name: 'Settings' } }"
	>
		<template #intro>
			The returns, payments and forms the statutory calendar makes filings for. Standard ones
			come with the app and stay current with each update; add your own for anything else.
		</template>
		<template #actions>
			<Button
				variant="solid"
				icon-left="lucide-plus"
				:label="isMobile ? 'Add' : 'Add an obligation'"
				:route="{ name: 'ObligationNew' }"
			/>
		</template>
	</RecordList>
</template>

<script setup>
// Every obligation template, grouped by law: what the calendar files for, and which are switched off.
import { computed, onMounted, ref } from "vue";
import { Button } from "frappe-ui";
import { call } from "@/api";
import RecordList from "@/components/RecordList.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import {
	OBLIGATION_FIELDS,
	OBLIGATION_LIST,
	obligationRow,
	obligationViews,
} from "@/lib/obligations";

const isMobile = useIsMobile();
// Laws in the order the library lists them: GST first, then income tax and the rest.
const laws = ref([]);
const views = computed(() => obligationViews(laws.value));

function empty(view, searching) {
	if (searching) return { title: "No matches", detail: "Try another word, or look under All." };
	return view === "off"
		? {
				title: "Nothing is switched off",
				detail: "Switch off an obligation your clients never have, and it appears here.",
		  }
		: {
				title: "The library is empty",
				detail: "Add the returns and payments the calendar should make filings for.",
				action: { label: "Add an obligation", route: { name: "ObligationNew" } },
		  };
}

onMounted(async () => {
	try {
		laws.value = (await call("kxcompliance.api.obligation_form_options")).law;
	} catch {
		// Without the order the laws still group, in the order their rows come.
		laws.value = [];
	}
});
</script>
