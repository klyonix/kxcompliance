<template>
	<RecordList
		list-key="reminder-log"
		title="Reminder log"
		doctype="Compliance Reminder Log"
		:fields="LOG_FIELDS"
		:views="LOG_VIEWS"
		:to-row="logRow"
		search-field="sent_to"
		search-placeholder="Search by email address"
		:empty="empty"
		:parent="{ label: 'Settings', route: { name: 'Settings' } }"
		:by-client="false"
		date-label="Sent"
	/>
</template>

<script setup>
// Every reminder, escalation and summary the app sent, newest first, searchable by who it went to.
import RecordList from "@/components/RecordList.vue";
import { LOG_FIELDS, LOG_VIEWS, logRow } from "@/lib/reminderLog";

function empty(view, searching) {
	if (searching)
		return { title: "Nothing sent to that address", detail: "Try part of the address." };
	return {
		title: "Nothing sent yet",
		detail: "Reminders go out once a day once they are switched on in Settings, and each one is kept here.",
	};
}
</script>
