<template>
	<AppPageHeader
		title="Customer and supplier licences"
		:parent="{ label: 'Settings', route: { name: 'Settings' } }"
	>
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
	</AppPageHeader>

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-6 sm:px-6">
		<p class="text-base text-ink-gray-6">
			Which licences a customer or supplier must hold before you sell to or buy from them. A
			rule blocks the document, or only warns, when the licence is missing or expired.
		</p>
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<div v-else-if="!rules" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton v-for="index in 4" :key="index" class="h-12 w-full rounded-lg" />
		</div>
		<div v-else-if="!rules.length" class="flex flex-col items-center gap-2 py-12 text-center">
			<p class="text-lg font-medium text-ink-gray-8">No rules yet</p>
			<p class="max-w-sm text-base text-ink-gray-5">
				Add one for each licence your customers or suppliers must hold, such as an FSSAI
				licence or a drug licence.
			</p>
			<Button
				class="mt-2"
				variant="solid"
				label="Add the first rule"
				:route="{ name: 'LicenceRuleNew' }"
			/>
		</div>
		<ul v-else class="flex flex-col" data-tour="licence-rules-list">
			<li v-for="rule in rules" :key="rule.name">
				<RouterLink
					:to="{ name: 'LicenceRule', params: { name: rule.name } }"
					class="flex items-center gap-3 rounded-lg px-3 py-2.5 hover:bg-surface-gray-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4"
				>
					<span class="flex min-w-0 flex-1 flex-col">
						<span
							class="truncate text-base font-medium"
							:class="rule.is_active ? 'text-ink-gray-8' : 'text-ink-gray-5'"
							>{{ rule.item_type }}</span
						>
						<span class="truncate text-sm text-ink-gray-5">{{
							ruleSummary(rule, documents)
						}}</span>
					</span>
					<Badge
						:label="rule.is_active ? rule.action : 'Off'"
						:theme="
							!rule.is_active ? 'gray' : rule.action === 'Block' ? 'red' : 'amber'
						"
					/>
				</RouterLink>
			</li>
		</ul>
	</div>
</template>

<script setup>
// Every licence rule, with what it checks and whether it blocks or warns.
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { Badge, Button, Skeleton } from "frappe-ui";
import { call, getList } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { RULE_FIELDS, ruleSummary } from "@/lib/licenceRules";
import { notLoaded } from "@/offline/reachability";

const isMobile = useIsMobile();
const rules = ref(null);
const documents = ref([]);
const error = ref("");

onMounted(async () => {
	try {
		const [options, list] = await Promise.all([
			call("kxcompliance.api.licence_rule_options"),
			getList("Licence Requirement", {
				fields: RULE_FIELDS,
				orderBy: "item_type asc",
				limit: 500,
			}),
		]);
		documents.value = options.documents;
		rules.value = list.rows;
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("the licence rules") : err.message;
	}
});
</script>
