<template>
	<AppPageHeader title="Companies" :parent="{ label: 'Settings', route: { name: 'Settings' } }">
		<template #actions>
			<Button
				variant="solid"
				icon-left="lucide-plus"
				label="Set up a company"
				:route="{ name: 'CompanyNew' }"
			/>
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
		<div v-else-if="!data" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton v-for="index in 4" :key="index" class="h-12 w-full rounded-lg" />
		</div>

		<template v-else>
			<section class="flex flex-col gap-1" aria-labelledby="set-up-heading">
				<h2 id="set-up-heading" class="pb-2 text-base font-semibold text-ink-gray-8">
					Set up for compliance
				</h2>
				<p v-if="!data.companies.length" class="text-base text-ink-gray-5">
					No company is set up yet.
				</p>
				<RouterLink
					v-for="company in data.companies"
					:key="company.company"
					:to="{ name: 'Company', params: { company: company.company } }"
					class="flex items-center gap-3 rounded-lg px-3 py-2.5 hover:bg-surface-gray-2"
				>
					<span
						class="lucide-building-2 size-4 shrink-0 text-ink-gray-5"
						aria-hidden="true"
					/>
					<span class="flex min-w-0 flex-1 flex-col">
						<span class="truncate text-base font-medium text-ink-gray-8">{{
							company.company
						}}</span>
						<span class="truncate text-sm text-ink-gray-5">{{
							[company.company_type, company.client].filter(Boolean).join(" · ")
						}}</span>
					</span>
					<span class="shrink-0 text-sm text-ink-gray-6">
						{{ company.registrations }} registrations ·
						{{ company.obligations }} obligations
					</span>
				</RouterLink>
			</section>

			<section
				v-if="data.not_set_up.length"
				class="flex flex-col gap-1"
				aria-labelledby="not-set-up-heading"
			>
				<h2 id="not-set-up-heading" class="pb-2 text-base font-semibold text-ink-gray-8">
					In ERPNext, not set up yet
				</h2>
				<RouterLink
					v-for="company in data.not_set_up"
					:key="company"
					:to="{ name: 'CompanyNew', query: { company } }"
					class="flex items-center gap-3 rounded-lg px-3 py-2.5 hover:bg-surface-gray-2"
				>
					<span
						class="lucide-building size-4 shrink-0 text-ink-gray-4"
						aria-hidden="true"
					/>
					<span class="min-w-0 flex-1 truncate text-base text-ink-gray-7">{{
						company
					}}</span>
					<span class="shrink-0 text-sm text-ink-blue-4">Set up</span>
				</RouterLink>
			</section>
		</template>
	</div>
</template>

<script setup>
// Which companies are set up for compliance, and a way to set up the rest.
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { Button, Skeleton } from "frappe-ui";
import { call } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { notLoaded } from "@/offline/reachability";

const data = ref(null);
const error = ref("");

onMounted(async () => {
	try {
		data.value = await call("kxcompliance.api.companies_overview");
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("the companies") : err.message;
	}
});
</script>
