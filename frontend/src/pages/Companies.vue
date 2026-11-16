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
		<ClientPicker :company-choice="false" />
		<div v-if="data" class="flex flex-wrap items-center gap-2" data-tour="companies-filter">
			<TextInput
				v-model="search"
				type="search"
				placeholder="Search companies"
				aria-label="Search companies"
				class="min-w-0 flex-1 sm:w-64 sm:flex-none"
			>
				<template #prefix
					><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true"
				/></template>
			</TextInput>
			<TabButtons v-model="show" :options="SHOW" />
		</div>
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
			<template v-if="filtered">
				<p class="text-lg font-medium text-ink-gray-8">No company matches</p>
				<p class="max-w-sm text-base text-ink-gray-5">
					Try other words, another client, or show every company.
				</p>
			</template>
			<template v-else>
				<p class="text-lg font-medium text-ink-gray-8">No company yet</p>
				<p class="max-w-sm text-base text-ink-gray-5">
					Set up the companies whose filings, licences and legal work you keep.
				</p>
			</template>
		</div>
		<RowList
			v-else
			paged="companies"
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
import { Button, Skeleton, TabButtons, TextInput } from "frappe-ui";
import { call } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import ClientPicker from "@/components/ClientPicker.vue";
import RowList from "@/components/RowList.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { companyGroups, filterCompanies } from "@/lib/companies";
import { notLoaded } from "@/offline/reachability";
import { clientFilter, loadClients } from "@/stores/clientFilter";

const SHOW = [
	{ label: "All", value: "" },
	{ label: "Set up", value: "set-up" },
	{ label: "Not set up", value: "not-set-up" },
];

// A phone's header has room for a short label beside the title.
const isMobile = useIsMobile();
const data = ref(null);
const error = ref("");
const search = ref("");
const show = ref("");
// The client chosen at the top, the words searched and set up or not narrow the list.
const filtered = computed(() => Boolean(clientFilter.client || search.value.trim() || show.value));
const groups = computed(() =>
	companyGroups(
		filterCompanies(data.value, {
			client: clientFilter.client,
			text: search.value,
			show: show.value,
		})
	)
);

onMounted(async () => {
	loadClients();
	try {
		data.value = await call("kxcompliance.api.companies_overview");
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("the companies") : err.message;
	}
});
</script>
