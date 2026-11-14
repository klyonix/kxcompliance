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
	/>
</template>

<script setup>
import RecordList from "@/components/RecordList.vue";
import { FILING_VIEWS, TASK_LIST_FIELDS, taskRow } from "@/lib/filings";

const EMPTY = {
	open: {
		title: "Nothing to file",
		detail: "Returns, payments and forms from the statutory calendar appear here as they fall due.",
	},
	review: {
		title: "Nothing waiting for review",
		detail: "Filings sent for review appear here until a reviewer marks them filed.",
	},
	done: { title: "Nothing filed yet", detail: "Filed and closed filings are kept here." },
};

function empty(view, searching) {
	if (searching) return { title: "No matches", detail: "Try another word, or another tab." };
	return EMPTY[view];
}
</script>
