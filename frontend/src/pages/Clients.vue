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

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-5 px-4 py-6 sm:px-6">
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
		<ul v-else class="flex flex-col gap-1" data-tour="clients-list">
			<li v-for="client in clients" :key="client.name">
				<RouterLink
					:to="{ name: 'Client', params: { name: client.name } }"
					class="flex items-center gap-3 rounded-lg px-3 py-3 hover:bg-surface-gray-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4"
				>
					<ScoreBadge
						:score="client.lowest_score?.score ?? null"
						:title="
							client.lowest_score ? `Lowest: ${client.lowest_score.company}` : ''
						"
					/>
					<span class="flex min-w-0 flex-1 flex-col gap-0.5">
						<span class="truncate text-base font-medium text-ink-gray-8">{{
							client.name
						}}</span>
						<span class="truncate text-sm text-ink-gray-5">{{
							companiesLine(client.companies)
						}}</span>
					</span>
					<span class="shrink-0 text-right text-sm" :class="TONE[clientTheme(client)]">
						{{ clientAttention(client) }}
					</span>
				</RouterLink>
			</li>
		</ul>
	</div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { Button, Skeleton } from "frappe-ui";
import { call } from "@/api";
import { isManager } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import ScoreBadge from "@/components/ScoreBadge.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { clientAttention, clientTheme, companiesLine } from "@/lib/clients";
import { notLoaded } from "@/offline/reachability";

const isMobile = useIsMobile();

const TONE = {
	red: "font-medium text-ink-red-5",
	amber: "text-ink-amber-5",
	green: "text-ink-gray-5",
};

const clients = ref(null);
const error = ref("");

onMounted(async () => {
	try {
		clients.value = await call("kxcompliance.api.clients_overview");
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("your clients") : err.message;
	}
});
</script>
