<template>
	<AppPageHeader :title="client?.name || 'Client'">
		<template #actions>
			<Dropdown v-if="client" :options="menu" align="end">
				<Button variant="ghost" icon="lucide-ellipsis" label="More actions" />
			</Dropdown>
		</template>
	</AppPageHeader>

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-6 sm:px-6">
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<div v-else-if="!client" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton class="h-6 w-1/2 rounded" />
			<Skeleton class="mt-4 h-32 w-full rounded-lg" />
		</div>

		<template v-else>
			<section class="flex flex-col gap-2">
				<div class="flex flex-wrap items-center gap-2">
					<Badge
						:label="client.status"
						:theme="client.status === 'Active' ? 'green' : 'gray'"
						size="md"
					/>
					<span class="text-base" :class="TONE[clientTheme(client)]">{{
						clientAttention(client)
					}}</span>
				</div>
				<p class="text-base text-ink-gray-6">{{ people }}</p>
			</section>

			<section class="flex flex-col gap-3" aria-labelledby="companies-heading">
				<h2 id="companies-heading" class="text-base font-semibold text-ink-gray-8">
					Companies
				</h2>
				<p v-if="!client.companies.length" class="text-base text-ink-gray-5">
					No companies yet. Link a company's compliance profile to this client in the
					Desk.
				</p>
				<ul class="flex flex-col">
					<li
						v-for="company in client.companies"
						:key="company.company"
						class="flex items-center gap-3 border-b border-outline-gray-1 py-2.5 last:border-b-0"
					>
						<span
							class="lucide-building-2 size-4 text-ink-gray-5"
							aria-hidden="true"
						/>
						<span class="flex min-w-0 flex-1 flex-col">
							<span class="truncate text-base text-ink-gray-8">{{
								company.company
							}}</span>
							<span class="text-sm text-ink-gray-5">{{ company.company_type }}</span>
						</span>
						<span class="text-sm" :class="TONE[clientTheme(company)]">{{
							clientAttention(company)
						}}</span>
					</li>
				</ul>
			</section>

			<section class="flex flex-col gap-1" aria-labelledby="open-heading">
				<h2 id="open-heading" class="pb-2 text-base font-semibold text-ink-gray-8">
					Open filings
				</h2>
				<p v-if="!client.filings.length" class="text-base text-ink-gray-5">
					Nothing open.
				</p>
				<WorkRow
					v-for="filing in client.filings"
					:key="filing.name"
					:row="taskRow(filing)"
				/>
			</section>
		</template>
	</div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { Badge, Button, Dropdown, Skeleton } from "frappe-ui";
import { call } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import WorkRow from "@/components/WorkRow.vue";
import { learnNames, nameOf } from "@/composables/usePeople";
import { clientAttention, clientTheme } from "@/lib/clients";
import { taskRow } from "@/lib/filings";
import { deskRoute } from "@/navigation";
import { notLoaded } from "@/offline/reachability";

const props = defineProps({ name: { type: String, required: true } });

const TONE = {
	red: "font-medium text-ink-red-5",
	amber: "text-ink-amber-5",
	green: "text-ink-gray-6",
};

const client = ref(null);
const error = ref("");

const people = computed(() => {
	const manager = client.value.relationship_manager;
	const team = client.value.team.filter((user) => user !== manager).map(nameOf);
	return [manager && `Managed by ${nameOf(manager)}`, team.length && `Team: ${team.join(", ")}`]
		.filter(Boolean)
		.join(" · ");
});

const menu = computed(() => [
	{
		label: "Open in the Desk",
		icon: "lucide-app-window",
		onClick: () => (window.location.href = deskRoute("Compliance Client", props.name)),
	},
]);

async function load() {
	error.value = "";
	try {
		client.value = await call("compliance_plus.api.client_detail", { client: props.name });
		learnNames([client.value.relationship_manager, ...client.value.team]);
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this client", "opened") : err.message;
	}
}

watch(() => props.name, load);
onMounted(load);
</script>
