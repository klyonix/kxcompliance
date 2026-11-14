<template>
	<RecordList
		title="Due-date extensions"
		doctype="Compliance Due Date Extension"
		:fields="EXTENSION_FIELDS"
		:views="views"
		:to-row="extensionRow"
		search-field="obligation_template"
		search-placeholder="Search by return or form"
		:empty="empty"
		:parent="{ label: 'Filings', route: { name: 'Filings' } }"
		:by-client="false"
	>
		<template #actions>
			<Button
				variant="solid"
				icon-left="lucide-plus"
				:label="isMobile ? 'Extend' : 'Extend a due date'"
				:route="{ name: 'ExtensionNew' }"
			/>
		</template>
	</RecordList>
</template>

<script setup>
// The government's due-date extensions recorded on this site; each moves the open filings it covers.
import { Button } from "frappe-ui";
import RecordList from "@/components/RecordList.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { EXTENSION_FIELDS, extensionRow, extensionViews } from "@/lib/obligations";

const isMobile = useIsMobile();
const views = extensionViews();

const EMPTY = {
	current: {
		title: "No extensions running",
		detail: "When the government extends a due date, record it here and the open filings it covers move to the new date.",
	},
	past: {
		title: "No past extensions",
		detail: "Extensions whose new date has passed are kept here.",
	},
};

function empty(view, searching) {
	if (searching) return { title: "No matches", detail: "Try another word, or another tab." };
	return EMPTY[view];
}
</script>
