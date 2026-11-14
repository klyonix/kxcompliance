<template>
	<AppPageHeader title="Clients">
		<template #actions>
			<Button
				v-if="isManager()"
				variant="solid"
				icon-left="lucide-plus"
				label="Add client"
				href="/app/compliance-client/new"
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
		</div>
		<ul v-else class="flex flex-col gap-1">
			<li v-for="client in clients" :key="client.name">
				<RouterLink
					:to="{ name: 'Client', params: { name: client.name } }"
					class="flex items-center gap-3 rounded-lg px-3 py-3 hover:bg-surface-gray-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4"
				>
					<Avatar :label="client.name" size="lg" />
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
import { Avatar, Button, Skeleton } from "frappe-ui";
import { call } from "@/api";
import { isManager } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { clientAttention, clientTheme, companiesLine } from "@/lib/clients";
import { notLoaded } from "@/offline/reachability";

const TONE = {
	red: "font-medium text-ink-red-5",
	amber: "text-ink-amber-5",
	green: "text-ink-gray-5",
};

const clients = ref(null);
const error = ref("");

onMounted(async () => {
	try {
		clients.value = await call("compliance_plus.api.clients_overview");
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("your clients") : err.message;
	}
});
</script>
