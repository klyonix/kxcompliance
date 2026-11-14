<template>
	<RecordList
		title="Signatories"
		doctype="Signatory"
		:fields="SIGNATORY_FIELDS"
		:views="SIGNATORY_VIEWS"
		:to-row="signatoryRow"
		search-field="full_name"
		search-placeholder="Search by name"
		:empty="empty"
		:parent="{ label: 'Register', route: { name: 'Register', query: { view: 'dsc' } } }"
	>
		<template #actions>
			<Button
				v-if="mayRecord()"
				variant="solid"
				icon-left="lucide-plus"
				label="Add signatory"
				:route="{ name: 'SignatoryNew' }"
			/>
		</template>
	</RecordList>
</template>

<script setup>
import { Button } from "frappe-ui";
import { mayRecord } from "@/boot";
import RecordList from "@/components/RecordList.vue";
import { SIGNATORY_FIELDS, SIGNATORY_VIEWS, signatoryRow } from "@/lib/signatories";

function empty(view, searching) {
	if (searching) return { title: "No matches", detail: "Try another name." };
	return view === "active"
		? {
				title: "No signatories yet",
				detail: "Directors, partners and authorised signatories, who hold the DSCs.",
		  }
		: { title: "Nobody has left", detail: "Signatories who resign or retire appear here." };
}
</script>
