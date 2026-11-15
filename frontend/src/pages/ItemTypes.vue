<template>
	<RecordList
		title="Register item types"
		list-key="item-types"
		doctype="Compliance Item Type"
		:fields="TYPE_FIELDS"
		:views="TYPE_VIEWS"
		:to-row="typeRow"
		v-bind="TYPE_LIST"
		search-field="name"
		search-placeholder="Search by name"
		:by-client="false"
		:empty="empty"
		:parent="{ label: 'Settings', route: { name: 'Settings' } }"
	>
		<template #intro>
			A type sets how often its items renew, how long after expiry they still count, whether
			a certificate is needed, and when reminders go out.
		</template>
		<template #actions>
			<Button
				variant="solid"
				icon-left="lucide-plus"
				label="Add a type"
				:route="{ name: 'ItemTypeNew' }"
			/>
		</template>
	</RecordList>
</template>

<script setup>
import { Button } from "frappe-ui";
import RecordList from "@/components/RecordList.vue";
import { TYPE_FIELDS, TYPE_LIST, TYPE_VIEWS, typeRow } from "@/lib/itemTypes";

function empty(view, searching) {
	if (searching) return { title: "No matches", detail: "Try another name, or look under All." };
	return view === "off"
		? { title: "No type is switched off", detail: "Types you stop using appear here." }
		: {
				title: "No item types yet",
				detail: "Add the kinds of licence, registration and certificate you keep.",
				action: { label: "Add a type", route: { name: "ItemTypeNew" } },
		  };
}
</script>
