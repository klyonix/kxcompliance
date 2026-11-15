<template>
	<RecordList
		title="Data breaches"
		doctype="Personal Data Breach"
		:fields="BREACH_FIELDS"
		:views="BREACH_VIEWS"
		:to-row="breachRow"
		search-placeholder="Search by title"
		:empty="empty"
		:parent="{ label: 'Settings', route: { name: 'Settings' } }"
		:by-client="false"
	>
		<template #actions>
			<Button
				variant="solid"
				icon-left="lucide-plus"
				:label="isMobile ? 'Record' : 'Record a breach'"
				:route="{ name: 'BreachNew' }"
			/>
		</template>
	</RecordList>
</template>

<script setup>
// Personal data breaches, and whether the Data Protection Board and the people affected were told.
import { Button } from "frappe-ui";
import RecordList from "@/components/RecordList.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { BREACH_FIELDS, BREACH_VIEWS, breachRow } from "@/lib/privacy";

const isMobile = useIsMobile();

const EMPTY = {
	open: {
		title: "No breaches to report",
		detail: "If personal data is lost, stolen or seen by someone who should not see it, record it here at once. The Board is told within 72 hours.",
		action: { label: "Record a breach", route: { name: "BreachNew" } },
	},
	reported: {
		title: "No reported breaches",
		detail: "Breaches reported to the Board and the people affected are kept here.",
	},
};

function empty(view, searching) {
	if (searching) return { title: "No matches", detail: "Try another word, or another tab." };
	return EMPTY[view];
}
</script>
