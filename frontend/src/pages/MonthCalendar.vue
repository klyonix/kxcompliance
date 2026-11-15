<template>
	<AppPageHeader title="Calendar">
		<template #actions>
			<Button
				variant="ghost"
				icon="lucide-chevron-left"
				:label="`Previous ${view}`"
				@click="move(-1)"
			/>
			<Button label="Today" @click="goToday" />
			<Button
				variant="ghost"
				icon="lucide-chevron-right"
				:label="`Next ${view}`"
				@click="move(1)"
			/>
		</template>
	</AppPageHeader>

	<div class="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-6 sm:px-6">
		<ClientPicker />
		<div class="flex flex-wrap items-center justify-between gap-3">
			<h2 class="text-xl font-semibold text-ink-gray-9" aria-live="polite">
				{{ viewTitle(view, focus) }}
			</h2>
			<TabButtons v-model="view" :options="VIEWS" data-tour="calendar-views" />
		</div>

		<!-- What to show, in one line: the kinds, and whose and which. -->
		<div class="flex flex-wrap items-center gap-2" data-tour="calendar-filters">
			<Dropdown :options="kindOptions">
				<Button
					icon-left="lucide-layers"
					icon-right="lucide-chevron-down"
					:label="kindsLabel"
					data-tour="calendar-kinds"
				/>
			</Dropdown>
			<Button
				:variant="mine ? 'subtle' : 'ghost'"
				icon-left="lucide-user-round"
				label="Only mine"
				:aria-pressed="mine"
				@click="toggleMine"
			/>
			<Button
				:variant="openOnly ? 'subtle' : 'ghost'"
				icon-left="lucide-circle-dashed"
				label="Open only"
				:aria-pressed="openOnly"
				@click="openOnly = !openOnly"
			/>
			<div v-if="isManager() && people.length" class="w-44">
				<FormControl
					v-model="person"
					type="select"
					:options="[{ label: 'Everyone', value: '' }, ...people]"
					aria-label="Whose"
					@update:model-value="(value) => value && (mine = false)"
				/>
			</div>
		</div>

		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>

		<!-- Month: the grid of days; choose one to list what falls on it. -->
		<template v-if="view === 'month'">
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
							day.date === focus ? 'ring-2 ring-inset ring-outline-gray-4' : '',
						]"
						:aria-label="dayLabel(day)"
						:aria-pressed="day.date === focus"
						@click="focus = day.date"
						@dblclick="openDay(day.date)"
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
								:class="chipClass(event)"
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
				<div class="flex items-center justify-between gap-2 pb-1">
					<h2 id="day-heading" class="text-base font-semibold text-ink-gray-8">
						{{ formatDate(focus, { weekday: true }) }}
					</h2>
					<Button
						variant="ghost"
						size="sm"
						icon-right="lucide-arrow-right"
						label="Day view"
						@click="openDay(focus)"
					/>
				</div>
				<p v-if="!rowsOn(focus).length" class="text-base text-ink-gray-5">
					{{ loading ? "Loading…" : "Nothing on this day." }}
				</p>
				<WorkRow v-for="row in rowsOn(focus)" :key="row.key" :row="row" />
			</section>
		</template>

		<!-- Week: seven days side by side on a computer, one under another on a phone. -->
		<template v-else-if="view === 'week'">
			<div
				v-if="!isMobile"
				class="grid grid-cols-7 overflow-hidden rounded-lg border border-outline-gray-1"
				:aria-busy="loading"
				data-tour="calendar-grid"
			>
				<div
					v-for="day in week"
					:key="day.date"
					class="flex min-h-80 min-w-0 flex-col border-r border-outline-gray-1 last:border-r-0"
				>
					<button
						type="button"
						class="flex items-center gap-1.5 border-b border-outline-gray-1 bg-surface-gray-1 px-2 py-1.5 text-left text-xs font-medium text-ink-gray-5 hover:bg-surface-gray-2"
						:aria-label="`${dayLabel(day)}. Open the day`"
						@click="openDay(day.date)"
					>
						{{ WEEKDAYS[week.indexOf(day)] }}
						<span
							class="flex size-6 items-center justify-center rounded-full text-sm"
							:class="
								day.isToday
									? 'bg-surface-gray-9 font-semibold text-ink-gray-1'
									: 'text-ink-gray-8'
							"
							>{{ day.day }}</span
						>
					</button>
					<div class="flex flex-col gap-1 p-1.5">
						<RouterLink
							v-for="event in days[day.date] || []"
							:key="`${event.kind}-${event.name}`"
							:to="eventRoute(event)"
							class="flex flex-col gap-0.5 rounded px-1.5 py-1 text-xs hover:bg-surface-gray-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4"
							:class="chipClass(event)"
						>
							<span class="flex items-center gap-1">
								<span
									:class="kindOf(event.kind).dot"
									class="size-1.5 shrink-0 rounded-full"
									aria-hidden="true"
								/>
								<span v-if="event.time" class="tabular-nums">{{
									event.time
								}}</span>
							</span>
							<span class="line-clamp-3 break-words">{{ event.title }}</span>
						</RouterLink>
					</div>
				</div>
			</div>
			<div v-else class="flex flex-col gap-4" data-tour="calendar-grid">
				<section v-for="day in week" :key="day.date" class="flex flex-col gap-1">
					<button
						type="button"
						class="flex items-center gap-2 text-left text-sm font-semibold"
						:class="day.isToday ? 'text-ink-gray-9' : 'text-ink-gray-7'"
						@click="openDay(day.date)"
					>
						{{ formatDate(day.date, { weekday: true, year: false }) }}
						<Badge v-if="day.isToday" label="Today" theme="blue" />
					</button>
					<p v-if="!rowsOn(day.date).length" class="text-sm text-ink-gray-4">Nothing</p>
					<WorkRow v-for="row in rowsOn(day.date)" :key="row.key" :row="row" />
				</section>
			</div>
		</template>

		<!-- Day: everything on it, in the order of the day. -->
		<section v-else class="flex flex-col gap-1" :aria-busy="loading" data-tour="calendar-grid">
			<p v-if="!rowsOn(focus).length" class="py-10 text-center text-base text-ink-gray-5">
				{{ loading ? "Loading…" : "Nothing on this day." }}
			</p>
			<WorkRow v-for="row in rowsOn(focus)" :key="row.key" :row="row" />
		</section>
	</div>
</template>

<script setup>
// The calendar: filings, expiries, legal dates and documents due, by month, week or day. Filters
// narrow it to some kinds, to one's own or one person's, or to what is still open; each thing
// opens its record. The view and the date are kept in the address.
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { Badge, Button, Dropdown, FormControl, TabButtons } from "frappe-ui";
import { call } from "@/api";
import { boot, isManager } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import ClientPicker from "@/components/ClientPicker.vue";
import WorkRow from "@/components/WorkRow.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { formatDate } from "@/lib/format";
import {
	KINDS,
	VIEWS,
	eventRoute,
	eventRow,
	eventsByDay,
	filterEvents,
	kindOf,
	monthGrid,
	parseFocus,
	parseMonth,
	rangeFor,
	shiftFocus,
	viewTitle,
	weekDays,
} from "@/lib/monthCalendar";
import { isoDate } from "@/lib/obligations";
import { personOptions } from "@/lib/people";
import { notLoaded } from "@/offline/reachability";
import { chosenCompanies, loadClients } from "@/stores/clientFilter";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const CELL_LIMIT = 3;

const route = useRoute();
const router = useRouter();
const isMobile = useIsMobile();

const view = ref(
	VIEWS.some((option) => option.value === route.query.view) ? route.query.view : "month"
);
// An older link carries ?month=2026-11: it opens on today in that month, or on its 1st.
function startingFocus() {
	if (route.query.date) return parseFocus(route.query.date);
	if (route.query.month) {
		const today = isoDate(new Date());
		const { year, month } = parseMonth(route.query.month);
		const first = `${year}-${String(month + 1).padStart(2, "0")}-01`;
		return today.startsWith(first.slice(0, 7)) ? today : first;
	}
	return isoDate(new Date());
}
const focus = ref(startingFocus());

const events = ref([]);
const loading = ref(false);
const error = ref("");
const shown = ref(KINDS.map((kind) => kind.key));
// The kinds as a menu, each ticked while shown; the button says how many are.
const kindOptions = computed(() =>
	KINDS.map((kind) => ({
		label: kind.label,
		icon: shown.value.includes(kind.key) ? "lucide-square-check" : "lucide-square",
		onClick: () =>
			(shown.value = shown.value.includes(kind.key)
				? shown.value.filter((key) => key !== kind.key)
				: [...shown.value, kind.key]),
	}))
);
const kindsLabel = computed(() =>
	shown.value.length === KINDS.length
		? "Everything"
		: shown.value.length === 1
		? KINDS.find((kind) => kind.key === shown.value[0]).label
		: `${shown.value.length} of ${KINDS.length} kinds`
);
const mine = ref(route.query.mine === "1");
const openOnly = ref(false);
const person = ref("");
const people = ref([]);

const weeks = computed(() => monthGrid(parseMonth(focus.value.slice(0, 7))));
const week = computed(() => weekDays(focus.value));
const days = computed(() =>
	eventsByDay(
		filterEvents(events.value, {
			shown: shown.value,
			mine: mine.value,
			open: openOnly.value,
			person: person.value,
			user: boot.user,
		}),
		shown.value
	)
);
const rowsOn = (date) => (days.value[date] || []).map(eventRow);

const kindsOn = (date) =>
	KINDS.filter((kind) => (days.value[date] || []).some((event) => event.kind === kind.key));

const chipClass = (event) =>
	event.overdue
		? "bg-surface-red-1 text-ink-red-4"
		: event.done
		? "text-ink-gray-5 line-through"
		: "text-ink-gray-8";

function dayLabel(day) {
	const count = (days.value[day.date] || []).length;
	return `${formatDate(day.date, { weekday: true })}: ${
		count ? `${count} ${count === 1 ? "thing" : "things"}` : "nothing"
	}`;
}

// Each load takes a ticket, so a slow answer for a range already left cannot replace this one.
let latest = 0;
async function load() {
	const ticket = ++latest;
	loading.value = true;
	error.value = "";
	const { start, end } = rangeFor(view.value, focus.value);
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
	focus.value = shiftFocus(view.value, focus.value, by);
}

function goToday() {
	focus.value = isoDate(new Date());
}

function openDay(date) {
	focus.value = date;
	view.value = "day";
}

function toggleMine() {
	mine.value = !mine.value;
	if (mine.value) person.value = "";
}

async function loadPeople() {
	if (!isManager()) return;
	try {
		people.value = personOptions(await call("kxcompliance.api.people_options"));
	} catch {
		// Without the list the person filter is left out; the rest of the calendar works.
		people.value = [];
	}
}

// The view and date in the address; a load only when what is shown moves to another range.
watch([view, focus, mine], () => {
	router.replace({
		query: {
			...route.query,
			month: undefined,
			view: view.value === "month" ? undefined : view.value,
			date: focus.value,
			mine: mine.value ? "1" : undefined,
		},
	});
});
watch(
	() => JSON.stringify(rangeFor(view.value, focus.value)),
	() => {
		events.value = [];
		load();
	}
);
watch(chosenCompanies, load);

onMounted(() => {
	loadClients().then(load);
	loadPeople();
});
</script>
