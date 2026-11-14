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
				v-if="isMobile"
				variant="ghost"
				icon="lucide-pen-line"
				label="Signatories"
				:route="{ name: 'Signatories' }"
			/>
			<Button
				v-else
				icon-left="lucide-pen-line"
				label="Signatories"
				:route="{ name: 'Signatories' }"
			/>
			<Button
				v-if="mayRecord()"
				variant="solid"
				icon-left="lucide-plus"
				:label="isMobile ? 'New' : 'New item'"
				:route="{ name: 'ItemNew' }"
			/>
		</template>
	</RecordList>
</template>

<script setup>
import { Button } from "frappe-ui";
import { mayRecord } from "@/boot";
import RecordList from "@/components/RecordList.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { ITEM_LIST_FIELDS, REGISTER_VIEWS, itemRow } from "@/lib/items";

// The phone's header has room for short labels beside the title.
const isMobile = useIsMobile();

function empty(view, searching) {
	if (searching) return { title: "No matches", detail: "Try another word, or look under All." };
	return {
		title: view === "attention" ? "Nothing needs attention" : "No items yet",
		detail: "Licences, registrations, certificates, insurance and subscriptions appear here once they are recorded.",
		action:
			view !== "attention" && mayRecord()
				? { label: "Add the first item", route: { name: "ItemNew" } }
				: null,
	};
}
</script>
