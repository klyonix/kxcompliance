<template>
	<AppPageHeader title="Calendar">
		<template #actions>
			<Button
				variant="ghost"
				icon="lucide-chevron-left"
				label="Previous month"
				@click="move(-1)"
			/>
			<Button :label="isMobile ? 'Today' : 'This month'" @click="goToday" />
			<Button
				variant="ghost"
				icon="lucide-chevron-right"
				label="Next month"
				@click="move(1)"
			/>
		</template>
	</AppPageHeader>

	<div class="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-6 sm:px-6">
		<ClientPicker />
		<div class="flex flex-wrap items-center justify-between gap-3">
			<h2 class="text-xl font-semibold text-ink-gray-9" aria-live="polite">
				{{ monthTitle(month) }}
			</h2>
			<fieldset class="flex flex-wrap gap-x-4 gap-y-1" data-tour="calendar-kinds">
				<legend class="sr-only">Show</legend>
				<label
					v-for="kind in KINDS"
					:key="kind.key"
					class="flex cursor-pointer items-center gap-1.5 text-sm text-ink-gray-7"
				>
					<input
						v-model="shown"
						type="checkbox"
						:value="kind.key"
						class="rounded border-outline-gray-3"
					/>
					<span :class="kind.dot" class="size-2 rounded-full" aria-hidden="true" />
					{{ kind.label }}
				</label>
			</fieldset>
		</div>

		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>

		<div
			class="overflow-hidden rounded-lg border border-outline-gray-1"
			:aria-busy="loading"
			data-tour="calendar-grid"
		>
			<div
				class="grid grid-cols-7 border-b border-outline-gray-1 bg-surface-gray-1 text-center text-xs font-medium text-ink-gray-5"
				aria-hidden="true"
			>
				<span v-for="name in WEEKDAYS" :key="name" class="py-1.5">{{
					isMobile ? name[0] : name
				}}</span>
			</div>
			<div v-for="(week, index) in weeks" :key="index" class="grid grid-cols-7">
				<button
					v-for="day in week"
					:key="day.date"
					type="button"
					class="flex min-h-14 flex-col gap-1 border-b border-r border-outline-gray-1 p-1 text-left last:border-r-0 focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-outline-gray-4 sm:min-h-28 sm:p-1.5"
					:class="[
						day.inMonth ? 'bg-surface-base' : 'bg-surface-gray-1',
						day.date === selected ? 'ring-2 ring-inset ring-outline-gray-4' : '',
					]"
					:aria-label="dayLabel(day)"
					:aria-pressed="day.date === selected"
					@click="selected = day.date"
				>
					<span
						class="flex size-6 items-center justify-center rounded-full text-sm"
						:class="
							day.isToday
								? 'bg-surface-gray-9 font-semibold text-ink-gray-1'
								: day.inMonth
								? 'text-ink-gray-8'
								: 'text-ink-gray-4'
						"
						>{{ day.day }}</span
					>
					<!-- Phones: a dot per kind. Computers: the first few by name. -->
					<span v-if="isMobile" class="flex flex-wrap gap-0.5 px-0.5">
						<span
							v-for="kind in kindsOn(day.date)"
							:key="kind.key"
							:class="kind.dot"
							class="size-1.5 rounded-full"
						/>
					</span>
					<template v-else>
						<span
							v-for="event in (days[day.date] || []).slice(0, CELL_LIMIT)"
							:key="`${event.kind}-${event.name}`"
							class="flex w-full items-center gap-1 truncate rounded px-1 py-0.5 text-xs"
							:class="
								event.overdue
									? 'bg-surface-red-1 text-ink-red-4'
									: event.done
									? 'text-ink-gray-5 line-through'
									: 'text-ink-gray-8'
							"
						>
							<span
								:class="kindOf(event.kind).dot"
								class="size-1.5 shrink-0 rounded-full"
								aria-hidden="true"
							/>
							<span class="truncate">{{ event.title }}</span>
						</span>
						<span
							v-if="(days[day.date] || []).length > CELL_LIMIT"
							class="px-1 text-xs text-ink-gray-5"
							>{{ days[day.date].length - CELL_LIMIT }} more</span
						>
					</template>
				</button>
			</div>
		</div>

		<section class="flex flex-col gap-1" aria-labelledby="day-heading">
			<h2 id="day-heading" class="pb-1 text-base font-semibold text-ink-gray-8">
				{{ formatDate(selected, { weekday: true }) }}
			</h2>
			<p v-if="!selectedEvents.length" class="text-base text-ink-gray-5">
				{{ loading ? "Loading…" : "Nothing on this day." }}
			</p>
			<WorkRow v-for="event in selectedEvents" :key="event.key" :row="event" />
		</section>
	</div>
</template>

<script setup>
// A month at a glance: filings, expiries, legal dates and documents due, on their days. Choose a
// day to list what falls on it; each opens its record.
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button } from "frappe-ui";
import { call } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import ClientPicker from "@/components/ClientPicker.vue";
import WorkRow from "@/components/WorkRow.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { formatDate } from "@/lib/format";
import {
	KINDS,
	eventRow,
	eventsByDay,
	gridRange,
	kindOf,
	monthGrid,
	monthKey,
	monthTitle,
	parseMonth,
	shiftMonth,
} from "@/lib/monthCalendar";
import { isoDate } from "@/lib/obligations";
import { notLoaded } from "@/offline/reachability";
import { chosenCompanies, loadClients } from "@/stores/clientFilter";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const CELL_LIMIT = 3;

const route = useRoute();
const router = useRouter();
const isMobile = useIsMobile();
const month = ref(parseMonth(route.query.month));
const events = ref([]);
const loading = ref(false);
const error = ref("");
const shown = ref(KINDS.map((kind) => kind.key));

const weeks = computed(() => monthGrid(month.value));
const days = computed(() => eventsByDay(events.value, shown.value));
const firstOfMonth = () =>
	weeks.value.flat().find((day) => day.isToday && day.inMonth)?.date ||
	`${monthKey(month.value)}-01`;
const selected = ref(firstOfMonth());
const selectedEvents = computed(() => (days.value[selected.value] || []).map(eventRow));

const kindsOn = (date) =>
	KINDS.filter((kind) => (days.value[date] || []).some((event) => event.kind === kind.key));

function dayLabel(day) {
	const count = (days.value[day.date] || []).length;
	return `${formatDate(day.date, { weekday: true })}: ${
		count ? `${count} ${count === 1 ? "thing" : "things"}` : "nothing"
	}`;
}

// Each load takes a ticket, so a slow answer for a month already left cannot replace this one.
let latest = 0;
async function load() {
	const ticket = ++latest;
	loading.value = true;
	error.value = "";
	const { start, end } = gridRange(weeks.value);
	try {
		const params = { start, end };
		if (chosenCompanies.value) params.companies = chosenCompanies.value;
		const result = await call("kxcompliance.api.month_events", params);
		if (ticket === latest) events.value = result;
	} catch (err) {
		if (ticket === latest)
			error.value = err.isNetwork ? notLoaded("the calendar") : err.message;
	} finally {
		if (ticket === latest) loading.value = false;
	}
}

function move(by) {
	month.value = shiftMonth(month.value, by);
}

function goToday() {
	month.value = parseMonth("");
	selected.value = isoDate(new Date());
}

watch(month, () => {
	router.replace({ query: { ...route.query, month: monthKey(month.value) } });
	if (!selected.value.startsWith(monthKey(month.value))) selected.value = firstOfMonth();
	events.value = [];
	load();
});
watch(chosenCompanies, load);

onMounted(() => loadClients().then(load));
</script>
