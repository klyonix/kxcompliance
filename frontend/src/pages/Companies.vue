<template>
	<AppPageHeader title="Companies" :parent="{ label: 'Settings', route: { name: 'Settings' } }">
		<template #actions>
			<Button
				variant="solid"
				icon-left="lucide-plus"
				:label="isMobile ? 'Set up' : 'Set up a company'"
				:route="{ name: 'CompanyNew' }"
			/>
		</template>
	</AppPageHeader>

	<div class="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-6 sm:px-6">
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<div v-else-if="!data" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton v-for="index in 4" :key="index" class="h-12 w-full rounded-lg" />
		</div>
		<div v-else-if="!groups.length" class="flex flex-col items-center gap-2 py-16 text-center">
			<p class="text-lg font-medium text-ink-gray-8">No company yet</p>
			<p class="max-w-sm text-base text-ink-gray-5">
				Set up the companies whose filings, licences and legal work you keep.
			</p>
		</div>
		<RowList
			v-else
			:groups="groups"
			:columns="[{ label: 'Registrations' }, { label: 'Obligations' }]"
			name-label="Company"
			:date-label="null"
		/>
	</div>
</template>

<script setup>
// Which companies are set up for compliance, and a way to set up the rest.
import { computed, onMounted, ref } from "vue";
import { Button, Skeleton } from "frappe-ui";
import { call } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import RowList from "@/components/RowList.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { companyGroups } from "@/lib/companies";
import { notLoaded } from "@/offline/reachability";

// A phone's header has room for a short label beside the title.
const isMobile = useIsMobile();
const data = ref(null);
const error = ref("");
const groups = computed(() => companyGroups(data.value));

onMounted(async () => {
	try {
		data.value = await call("kxcompliance.api.companies_overview");
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("the companies") : err.message;
	}
});
</script>
