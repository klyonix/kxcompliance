<template>
	<RecordList
		title="Register"
		doctype="Compliance Item"
		:fields="ITEM_LIST_FIELDS"
		:views="REGISTER_VIEWS"
		:to-row="itemRow"
		search-placeholder="Search the register"
		:empty="empty"
	>
		<template #actions>
			<Button
				icon-left="lucide-pen-line"
				label="Signatories"
				:route="{ name: 'Signatories' }"
			/>
		</template>
	</RecordList>
</template>

<script setup>
import { Button } from "frappe-ui";
import RecordList from "@/components/RecordList.vue";
import { ITEM_LIST_FIELDS, REGISTER_VIEWS, itemRow } from "@/lib/items";

function empty(view, searching) {
	if (searching) return { title: "No matches", detail: "Try another word, or look under All." };
	return {
		title: view === "attention" ? "Nothing needs attention" : "No items yet",
		detail: "Licences, registrations, certificates, insurance and subscriptions appear here once they are recorded.",
	};
}
</script>
