<template>
	<RecordList
		list-key="privacy-requests"
		title="Privacy requests"
		doctype="Privacy Request"
		:fields="REQUEST_FIELDS"
		:views="REQUEST_VIEWS"
		:to-row="requestRow"
		search-field="requester_name"
		search-placeholder="Search by name"
		:empty="empty"
		:parent="{ label: 'Settings', route: { name: 'Settings' } }"
		:by-client="false"
	/>
</template>

<script setup>
// What people have asked about their own data, for a manager to answer within 90 days.
import RecordList from "@/components/RecordList.vue";
import { REQUEST_FIELDS, REQUEST_VIEWS, requestRow } from "@/lib/privacy";

const EMPTY = {
	open: {
		title: "Nothing to answer",
		detail: "When someone asks from Account to see, correct or erase their data, or raises a grievance, it comes here.",
	},
	closed: { title: "No answered requests", detail: "Answered requests are kept here." },
};

function empty(view, searching) {
	if (searching) return { title: "No matches", detail: "Try another name, or another tab." };
	return EMPTY[view];
}
</script>
