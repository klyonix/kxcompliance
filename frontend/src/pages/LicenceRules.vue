<template>
	<RecordList
		title="Customer and supplier licences"
		list-key="licence-rules"
		doctype="Licence Requirement"
		:fields="RULE_FIELDS"
		:views="RULE_VIEWS"
		:to-row="(rule) => ruleRow(rule, documents)"
		v-bind="RULE_LIST"
		search-field="item_type"
		search-placeholder="Search by licence"
		:by-client="false"
		:empty="empty"
		:parent="{ label: 'Settings', route: { name: 'Settings' } }"
	>
		<template #intro>
			Which licences a customer or supplier must hold before you sell to or buy from them. A
			rule blocks the document, or only warns, when the licence is missing or expired.
		</template>
		<template #actions>
			<Button
				icon-left="lucide-shield-alert"
				:label="isMobile ? 'Blocks' : 'Blocks and warnings'"
				:route="{ name: 'LicenceBlocks' }"
			/>
			<Button
				variant="solid"
				icon-left="lucide-plus"
				:label="isMobile ? 'Add' : 'Add a rule'"
				:route="{ name: 'LicenceRuleNew' }"
			/>
		</template>
	</RecordList>
</template>

<script setup>
// Every licence rule, with what it checks and whether it blocks or warns.
import { onMounted, ref } from "vue";
import { Button } from "frappe-ui";
import { call } from "@/api";
import RecordList from "@/components/RecordList.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { RULE_FIELDS, RULE_LIST, RULE_VIEWS, ruleRow } from "@/lib/licenceRules";

const isMobile = useIsMobile();
// Which documents each rule can check, for the line under its name.
const documents = ref([]);

function empty(view, searching) {
	if (searching)
		return { title: "No matches", detail: "Try another licence, or look under All." };
	return view === "off"
		? { title: "No rule is switched off", detail: "Rules you stop checking appear here." }
		: {
				title: "No licence rules yet",
				detail: "Add a rule for each licence a customer or supplier must hold.",
				action: { label: "Add a rule", route: { name: "LicenceRuleNew" } },
		  };
}

onMounted(async () => {
	try {
		documents.value = (await call("kxcompliance.api.licence_rule_options")).documents;
	} catch {
		// Without them each rule still shows; only the documents it checks are left out.
		documents.value = [];
	}
});
</script>
