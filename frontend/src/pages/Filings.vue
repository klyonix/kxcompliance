<template>
	<RecordList
		title="Filings"
		doctype="Compliance Task"
		:fields="TASK_LIST_FIELDS"
		:views="FILING_VIEWS"
		:to-row="taskRow"
		search-field="obligation_template"
		search-placeholder="Search by return or form"
		:empty="empty"
	>
		<template #actions>
			<template v-if="isManager()">
				<Button
					v-if="isMobile"
					variant="ghost"
					icon="lucide-calendar-clock"
					label="Due-date extensions"
					:route="{ name: 'Extensions' }"
				/>
				<Button
					v-else
					icon-left="lucide-calendar-clock"
					label="Extensions"
					:route="{ name: 'Extensions' }"
				/>
			</template>
			<template v-if="mayRecord()">
				<Button
					v-if="isMobile"
					variant="ghost"
					icon="lucide-list-checks"
					label="File in bulk"
					:route="{ name: 'BulkFiling' }"
				/>
				<Button
					v-else
					icon-left="lucide-list-checks"
					label="File in bulk"
					:route="{ name: 'BulkFiling' }"
				/>
			</template>
			<Button
				v-if="mayRecord()"
				variant="solid"
				icon-left="lucide-plus"
				:label="isMobile ? 'Log event' : 'Record an event'"
				:route="{ name: 'RecordEvent' }"
			/>
		</template>
	</RecordList>
</template>

<script setup>
import { Button } from "frappe-ui";
import { isManager, mayRecord } from "@/boot";
import RecordList from "@/components/RecordList.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { FILING_VIEWS, TASK_LIST_FIELDS, taskRow } from "@/lib/filings";

// The phone's header has room for a short label beside the title.
const isMobile = useIsMobile();

const EMPTY = {
	open: {
		title: "Nothing to file",
		detail: "Returns, payments and forms appear here as they fall due, from each company's registrations.",
	},
	review: {
		title: "Nothing waiting for review",
		detail: "Filings sent for review appear here until a reviewer marks them filed.",
	},
	done: { title: "Nothing filed yet", detail: "Filed and closed filings are kept here." },
};

function empty(view, searching) {
	if (searching) return { title: "No matches", detail: "Try another word, or another tab." };
	// A manager with nothing to file may not have set up any company's registrations yet.
	const action =
		view === "open" && isManager()
			? { label: "Set up companies", route: { name: "Companies" } }
			: null;
	return { ...EMPTY[view], action };
}
</script>
