<template>
	<AppPageHeader
		title="Obligation library"
		:parent="{ label: 'Settings', route: { name: 'Settings' } }"
	>
		<template #actions>
			<Button
				variant="solid"
				icon-left="lucide-plus"
				:label="isMobile ? 'Add' : 'Add an obligation'"
				:route="{ name: 'ObligationNew' }"
			/>
		</template>
	</AppPageHeader>

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-6 sm:px-6">
		<p class="text-base text-ink-gray-6">
			The returns, payments and forms the statutory calendar makes filings for. Standard ones
			come with the app and stay current with each update; add your own for anything else.
		</p>
		<div class="flex flex-col gap-2 sm:flex-row sm:items-center">
			<TextInput
				v-model="search"
				class="sm:flex-1"
				type="search"
				placeholder="Search by name, form or law"
				aria-label="Search obligations"
			>
				<template #prefix>
					<span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
				</template>
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
		<div v-else-if="!templates" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton v-for="index in 6" :key="index" class="h-12 w-full rounded-lg" />
		</div>
		<div v-else-if="!groups.length" class="py-10 text-center">
			<p class="text-base font-medium text-ink-gray-8">No obligations match</p>
			<p class="mt-1 text-sm text-ink-gray-5">Try another word, or show all of them.</p>
		</div>
		<section
			v-for="group in groups"
			v-else
			:key="group.law"
			class="flex flex-col"
			:aria-labelledby="`law-${group.law}`"
		>
			<h2
				:id="`law-${group.law}`"
				class="px-3 pb-1 pt-3 text-sm font-semibold text-ink-gray-6"
			>
				{{ group.law }}
			</h2>
			<ul class="flex flex-col">
				<li v-for="template in group.templates" :key="template.name">
					<RouterLink
						:to="{ name: 'Obligation', params: { name: template.name } }"
						class="flex items-center gap-3 rounded-lg px-3 py-2.5 hover:bg-surface-gray-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4"
					>
						<span class="flex min-w-0 flex-1 flex-col">
							<span
								class="truncate text-base font-medium"
								:class="template.is_active ? 'text-ink-gray-8' : 'text-ink-gray-5'"
								>{{ template.name }}</span
							>
							<span class="truncate text-sm text-ink-gray-5">{{
								ruleSummary(template)
							}}</span>
						</span>
						<Badge v-if="!template.is_standard" label="Your own" theme="blue" />
						<span v-if="!template.is_active" class="text-sm text-ink-gray-5"
							>Switched off</span
						>
					</RouterLink>
				</li>
			</ul>
		</section>
	</div>
</template>

<script setup>
// Every obligation template, grouped by law: what the calendar files for, and which are switched off.
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { Badge, Button, Skeleton, TabButtons, TextInput } from "frappe-ui";
import { call, getList } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { groupByLaw, matchesSearch, ruleSummary } from "@/lib/obligations";
import { notLoaded } from "@/offline/reachability";

const SHOW = [
	{ label: "In use", value: "active" },
	{ label: "Off", value: "off" },
	{ label: "All", value: "all" },
];

const isMobile = useIsMobile();
const templates = ref(null);
const laws = ref([]);
const error = ref("");
const search = ref("");
const show = ref("active");

const groups = computed(() =>
	groupByLaw(
		templates.value.filter(
			(template) =>
				(show.value === "all" ||
					Boolean(template.is_active) === (show.value === "active")) &&
				matchesSearch(template, search.value)
		),
		laws.value
	)
);

onMounted(async () => {
	try {
		const [options, list] = await Promise.all([
			call("kxcompliance.api.obligation_form_options"),
			getList("Compliance Obligation Template", {
				fields: [
					"name",
					"law",
					"form",
					"frequency",
					"months_after_period",
					"due_day",
					"due_after_event",
					"days_after_event",
					"event_type",
					"is_active",
					"is_standard",
				],
				orderBy: "name asc",
				limit: 1000,
			}),
		]);
		// Laws in the order the library lists them: GST first, then income tax and the rest.
		laws.value = options.law;
		templates.value = list.rows;
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("the obligation library") : err.message;
	}
});
</script>
