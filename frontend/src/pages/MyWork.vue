<template>
	<AppPageHeader title="My Work">
		<template #actions>
			<Button
				v-if="isMobile"
				variant="ghost"
				icon="lucide-calendar-days"
				label="Calendar"
				:route="{ name: 'MonthCalendar' }"
			/>
			<Button
				v-if="isMobile && isManager()"
				variant="ghost"
				icon="lucide-layout-dashboard"
				label="Overview"
				:route="{ name: 'Overview' }"
			/>
			<Button
				variant="ghost"
				icon="lucide-refresh-cw"
				label="Refresh"
				:loading="work.loading"
				@click="loadWork"
			/>
		</template>
	</AppPageHeader>

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6 sm:px-6">
		<div class="flex flex-col gap-1">
			<p class="text-xl font-semibold text-ink-gray-9">{{ greeting }}</p>
			<p class="text-base text-ink-gray-6">{{ summary }}</p>
		</div>

		<GettingStarted v-if="isManager()" />

		<ClientPicker />

		<TabButtons v-if="rows.length" v-model="filter" :options="filterOptions" />

		<p
			v-if="work.error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ work.error }}
		</p>

		<div v-if="phase === 'loading'" class="flex flex-col gap-4" aria-busy="true">
			<div v-for="index in 5" :key="index" class="flex items-center gap-3 px-3">
				<Skeleton class="size-8 rounded-full" />
				<div class="flex flex-1 flex-col gap-1.5">
					<Skeleton class="h-4 w-2/3 rounded" />
					<Skeleton class="h-3 w-1/3 rounded" />
				</div>
				<Skeleton class="h-3 w-16 rounded" />
			</div>
		</div>

		<p
			v-else-if="phase === 'tabEmpty'"
			class="px-3 py-10 text-center text-base text-ink-gray-5"
		>
			{{ TAB_EMPTY[filter] }}
		</p>

		<div
			v-else-if="phase === 'empty'"
			class="flex flex-col items-center gap-2 py-16 text-center"
		>
			<span
				class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-6"
			>
				<span class="lucide-circle-check size-6" aria-hidden="true" />
			</span>
			<p class="text-lg font-medium text-ink-gray-8">Nothing needs you right now</p>
			<p class="max-w-sm text-base text-ink-gray-5">
				Licences, filings and hearings you hold or review appear here as they come due.
			</p>
		</div>

		<section
			v-for="group in groups"
			:key="group.key"
			class="flex flex-col gap-1"
			:aria-labelledby="`group-${group.key}`"
		>
			<h2
				:id="`group-${group.key}`"
				class="flex items-baseline gap-2 px-3 pb-1 text-sm font-medium text-ink-gray-6"
			>
				{{ group.label }}<span class="text-ink-gray-4">{{ group.rows.length }}</span>
			</h2>
			<WorkRow v-for="row in group.rows" :key="row.key" :row="row" />
		</section>

		<p v-if="asOf" class="px-3 text-sm text-ink-gray-5">Updated {{ asOf }}</p>
	</div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { Button, Skeleton, TabButtons } from "frappe-ui";
import { boot, isManager } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import ClientPicker from "@/components/ClientPicker.vue";
import GettingStarted from "@/components/GettingStarted.vue";
import WorkRow from "@/components/WorkRow.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { BUCKETS } from "@/pages/myWork";
import { counts, loadWork, rows, work } from "@/stores/work";
import { formatDateTime } from "@/lib/format";

const isMobile = useIsMobile();

const filter = ref("all");
const TAB_EMPTY = {
	overdue: "Nothing is overdue.",
	week: "Nothing falls due in the next seven days.",
	later: "Nothing further out yet.",
};

const filterOptions = computed(() => [
	{ label: `All ${rows.value.length}`, value: "all" },
	...BUCKETS.map((bucket) => ({
		label: `${bucket.label} ${counts.value[bucket.key]}`,
		value: bucket.key,
	})),
]);

const shown = computed(() =>
	filter.value === "all" ? rows.value : rows.value.filter((row) => row.bucket === filter.value)
);

// Grouped by when things are due (RK chose this over grouping by kind).
const groups = computed(() =>
	BUCKETS.map((bucket) => ({
		key: bucket.key,
		label: bucket.label,
		rows: shown.value.filter((row) => row.bucket === bucket.key),
	})).filter((group) => group.rows.length)
);

const greeting = computed(() => {
	const hour = new Date().getHours();
	const part = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
	const first = (boot.userFullname || "").split(" ")[0];
	return first ? `${part}, ${first}` : part;
});

// What the page is showing, decided once so the summary line and the body always agree.
const phase = computed(() => {
	if (rows.value.length) return shown.value.length ? "rows" : "tabEmpty";
	if (work.error) return "failed";
	if (work.loading || !work.data) return "loading";
	return "empty";
});

const summary = computed(() => {
	if (phase.value === "failed") return "My Work could not be loaded.";
	if (phase.value === "loading") return "Looking at what is due…";
	if (phase.value === "empty") return "You are up to date.";
	const { overdue, week, later } = counts.value;
	const parts = [];
	if (overdue) parts.push(`${overdue} overdue`);
	if (week) parts.push(`${week} due this week`);
	if (later) parts.push(`${later} later`);
	return overdue ? `${parts.join(", ")}.` : `Nothing overdue. ${parts.join(", ")}.`;
});

const asOf = computed(() => formatDateTime(work.data?.as_of));

onMounted(loadWork);
</script>
