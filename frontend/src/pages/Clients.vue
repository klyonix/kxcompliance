<template>
	<AppPageHeader title="Clients">
		<template #actions>
			<!-- A phone's header has room for one labelled button. -->
			<Button
				v-if="isManager() && isMobile"
				variant="ghost"
				icon="lucide-sheet"
				label="Import from a sheet"
				:route="{ name: 'BulkSetup' }"
			/>
			<Button
				v-else-if="isManager()"
				icon-left="lucide-sheet"
				label="Import from a sheet"
				:route="{ name: 'BulkSetup' }"
			/>
			<Button
				v-if="isManager()"
				variant="solid"
				icon-left="lucide-plus"
				label="Add client"
				:route="{ name: 'ClientNew' }"
			/>
		</template>
	</AppPageHeader>

	<div class="mx-auto flex w-full max-w-6xl flex-col gap-5 px-4 py-6 sm:px-6">
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<div v-else-if="!clients" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton v-for="index in 5" :key="index" class="h-16 w-full rounded-lg" />
		</div>
		<div
			v-else-if="!clients.length"
			class="flex flex-col items-center gap-2 py-16 text-center"
		>
			<span
				class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-6"
			>
				<span class="lucide-users size-6" aria-hidden="true" />
			</span>
			<p class="text-lg font-medium text-ink-gray-8">No clients yet</p>
			<p class="max-w-sm text-base text-ink-gray-5">
				Clients you are on the team of appear here, with their companies and what is due.
			</p>
			<div v-if="isManager()" class="mt-2 flex flex-wrap justify-center gap-2">
				<Button variant="solid" label="Add a client" :route="{ name: 'ClientNew' }" />
				<Button label="Import from a sheet" :route="{ name: 'BulkSetup' }" />
			</div>
		</div>
		<template v-else>
			<TextInput
				v-model="search"
				type="search"
				placeholder="Search by client or company"
				aria-label="Search by client or company"
				class="w-full sm:w-72"
			>
				<template #prefix
					><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true"
				/></template>
			</TextInput>
			<p v-if="!rows.length" class="py-10 text-center text-base text-ink-gray-5">
				No client matches. Try another name.
			</p>
			<RowList
				v-else
				paged="clients"
				data-tour="clients-list"
				:rows="rows"
				:columns="[{ label: 'Lowest score' }, { label: 'What is due' }]"
				name-label="Client"
				:date-label="null"
			/>
		</template>
	</div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { Button, Skeleton, TextInput } from "frappe-ui";
import { call } from "@/api";
import { isManager } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import RowList from "@/components/RowList.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { clientLabel, clientRow } from "@/lib/clients";
import { notLoaded } from "@/offline/reachability";

const isMobile = useIsMobile();

const clients = ref(null);
const error = ref("");
const search = ref("");

// Every word typed must be in the client's name or one of its companies.
const rows = computed(() => {
	const words = search.value.toLowerCase().split(/\s+/).filter(Boolean);
	return clients.value
		.filter((client) => {
			const text = [clientLabel(client), ...client.companies].join(" ").toLowerCase();
			return words.every((word) => text.includes(word));
		})
		.map(clientRow);
});

onMounted(async () => {
	try {
		clients.value = await call("kxcompliance.api.clients_overview");
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("your clients") : err.message;
	}
});
</script>
