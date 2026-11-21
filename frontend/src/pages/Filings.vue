<template>
	<RecordList
		title="Filings"
		list-key="filings"
		doctype="Compliance Task"
		:fields="TASK_LIST_FIELDS"
		:views="FILING_VIEWS"
		:to-row="taskRow"
		v-bind="FILING_LIST"
		search-field="obligation_template"
		search-placeholder="Search by return or form"
		:empty="empty"
	>
		<template #actions>
			<!-- A phone's header has room for one more button: the rest go in a menu. -->
			<Dropdown v-if="isMobile && moreMenu.length" :options="moreMenu" align="end">
				<Button
					variant="ghost"
					icon="lucide-ellipsis"
					label="More"
					data-tour="filings-more"
				/>
			</Dropdown>
			<template v-else-if="!isMobile">
				<Button
					v-if="isManager()"
					data-tour="filings-extensions"
					icon-left="lucide-calendar-clock"
					label="Extensions"
					:route="{ name: 'Extensions' }"
				/>
				<Button
					v-if="mayRecord()"
					icon-left="lucide-file-plus"
					label="One-off filing"
					:route="{ name: 'NewFiling' }"
				/>
				<Button
					v-if="mayRecord()"
					data-tour="filings-bulk"
					icon-left="lucide-list-checks"
					label="File in bulk"
					:route="{ name: 'BulkFiling' }"
				/>
				<Button
					v-if="mayRecord()"
					icon-left="lucide-circle-dashed"
					label="File NIL together"
					:route="{ name: 'NilFiling' }"
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
import { computed } from "vue";
import { useRouter } from "vue-router";
import { Button, Dropdown } from "frappe-ui";
import { isManager, mayRecord } from "@/boot";
import RecordList from "@/components/RecordList.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { FILING_LIST, FILING_VIEWS, TASK_LIST_FIELDS, taskRow } from "@/lib/filings";

// The phone's header has room for a short label beside the title.
const isMobile = useIsMobile();
const router = useRouter();
const moreMenu = computed(() =>
	[
		mayRecord() && {
			label: "One-off filing",
			icon: "lucide-file-plus",
			onClick: () => router.push({ name: "NewFiling" }),
		},
		mayRecord() && {
			label: "File in bulk",
			icon: "lucide-list-checks",
			onClick: () => router.push({ name: "BulkFiling" }),
		},
		mayRecord() && {
			label: "File NIL together",
			icon: "lucide-circle-dashed",
			onClick: () => router.push({ name: "NilFiling" }),
		},
		isManager() && {
			label: "Due-date extensions",
			icon: "lucide-calendar-clock",
			onClick: () => router.push({ name: "Extensions" }),
		},
	].filter(Boolean)
);

const EMPTY = {
	open: {
		title: "Nothing to file",
		detail: "Returns, payments and forms appear here as they fall due, from each company's registrations.",
	},
	review: {
		title: "Nothing waiting for review",
		detail: "Filings sent for review appear here until a reviewer marks them filed.",
	},
	nil: {
		title: "No NIL returns to file",
		detail: "Mark a filing NIL from its page when there is nothing to report; it waits here until it is filed.",
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
