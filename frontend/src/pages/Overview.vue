<template>
	<AppPageHeader title="Overview">
		<template #actions>
			<Button
				variant="ghost"
				icon="lucide-refresh-cw"
				label="Refresh"
				:loading="loading"
				@click="load"
			/>
		</template>
	</AppPageHeader>

	<div class="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-6 sm:px-6">
		<!-- A firm sees every client's numbers, or one client's. -->
		<ClientPicker />
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>

		<div v-else-if="!data" class="flex flex-col gap-6" aria-busy="true">
			<Skeleton class="h-28 w-full rounded-lg" />
			<div v-for="section in 3" :key="section" class="grid grid-cols-2 gap-3 sm:grid-cols-4">
				<Skeleton v-for="index in 4" :key="index" class="h-20 rounded-lg" />
			</div>
		</div>

		<template v-else>
			<div class="flex flex-col gap-1">
				<h1 class="text-xl font-semibold text-ink-gray-9">{{ greeting }}</h1>
				<p class="text-base text-ink-gray-6">{{ today }}</p>
			</div>
			<UrgencyTiles :tiles="data.dashboard.urgency" />

			<section class="flex flex-col gap-3" aria-labelledby="needs-heading">
				<h2 id="needs-heading" class="text-base font-semibold text-ink-gray-8">
					Needs you now
				</h2>
				<div
					v-if="!needs.length"
					class="flex items-center gap-3 rounded-lg bg-surface-green-1 px-4 py-3"
				>
					<span
						class="lucide-circle-check size-5 shrink-0 text-ink-green-4"
						aria-hidden="true"
					/>
					<p class="text-base text-ink-gray-8">
						All clear: nothing overdue, expiring or waiting for review.
					</p>
				</div>
				<ul v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2">
					<li v-for="card in needs" :key="`${card.section}-${card.label}`">
						<component
							:is="opens(card, card.section) ? RouterLink : 'a'"
							v-bind="linkTo(card, card.section)"
							class="flex items-center gap-4 rounded-lg border border-outline-gray-1 px-4 py-3 hover:bg-surface-gray-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4"
						>
							<span
								class="w-10 shrink-0 text-2xl font-semibold tabular-nums"
								:class="valueClass(card)"
								>{{ card.value }}</span
							>
							<span class="flex min-w-0 flex-col">
								<span class="truncate text-base font-medium text-ink-gray-8">{{
									card.label
								}}</span>
								<span class="truncate text-sm text-ink-gray-5">{{
									card.section
								}}</span>
							</span>
						</component>
					</li>
				</ul>
			</section>

			<div class="grid grid-cols-1 gap-4 lg:grid-cols-2" data-tour="overview-charts">
				<div class="h-72 rounded-xl border border-outline-gray-1 p-4">
					<BarChart
						title="Falling due"
						subtitle="The next six months"
						:data="data.dashboard.due_by_month"
						x="month"
						:y="DUE_SERIES"
						stacked
					/>
				</div>
				<div class="h-72 rounded-xl border border-outline-gray-1 p-4">
					<BarChart
						title="Filings by month"
						subtitle="Filed on time, filed late, and not filed yet"
						:data="data.dashboard.filed_by_month"
						x="month"
						:y="FILED_SERIES"
						:series-config="FILED_COLOURS"
						stacked
					/>
				</div>
			</div>

			<section
				class="flex flex-col gap-3 rounded-lg border border-outline-gray-1 px-4 py-4"
				aria-labelledby="on-time-heading"
			>
				<div class="flex items-start justify-between gap-3">
					<h2 id="on-time-heading" class="text-base font-semibold text-ink-gray-8">
						Filed on time
					</h2>
					<RouterLink
						:to="{ name: 'Report', params: { report: 'on-time-filing' } }"
						class="text-sm text-ink-gray-6 underline decoration-outline-gray-3 underline-offset-2 hover:text-ink-gray-8"
						>Open the report</RouterLink
					>
				</div>
				<p class="flex flex-wrap items-baseline gap-x-2 gap-y-1">
					<span
						v-if="showPercent(data.on_time)"
						class="text-3xl font-semibold text-ink-gray-9"
						>{{ data.on_time.percent }}%</span
					>
					<span class="text-base text-ink-gray-6">{{
						onTimeSummary(data.on_time)
					}}</span>
				</p>
				<template v-if="parts.length">
					<div
						class="flex h-2 w-full overflow-hidden rounded-full bg-surface-gray-2"
						role="img"
						:aria-label="
							parts.map((part) => `${part.label}: ${part.count}`).join(', ')
						"
					>
						<span
							v-for="part in parts"
							:key="part.key"
							:class="part.colour"
							:style="{ width: `${part.share}%` }"
						/>
					</div>
					<ul class="flex flex-wrap gap-x-5 gap-y-1 text-sm text-ink-gray-6">
						<li
							v-for="part in parts"
							:key="part.key"
							class="flex items-center gap-1.5"
						>
							<span
								:class="part.colour"
								class="size-2 rounded-full"
								aria-hidden="true"
							/>
							{{ part.label }} {{ part.count }}
						</li>
					</ul>
				</template>
			</section>

			<div class="grid grid-cols-1 gap-8 lg:grid-cols-3">
				<section
					v-if="data.scores.length"
					class="flex flex-col gap-1 lg:col-span-2"
					aria-labelledby="scores-heading"
				>
					<div class="flex flex-col gap-0.5 pb-2">
						<h2 id="scores-heading" class="text-base font-semibold text-ink-gray-8">
							Compliance score
						</h2>
						<p class="text-sm text-ink-gray-5">
							Each company starts at 100 and loses points for what needs fixing; the
							lowest first.
						</p>
					</div>
					<RouterLink
						v-for="row in data.scores.slice(0, showAllScores ? undefined : 8)"
						:key="row.company"
						:to="{ name: 'Company', params: { company: row.company } }"
						class="flex items-center gap-3 rounded-lg px-3 py-2.5 hover:bg-surface-gray-2"
					>
						<ScoreBadge :score="row.score" />
						<span class="flex min-w-0 flex-1 flex-col">
							<span class="truncate text-base font-medium text-ink-gray-8">{{
								row.company
							}}</span>
							<span class="truncate text-sm text-ink-gray-5">{{
								row.reasons.length
									? row.reasons.map((reason) => reason.label).join(" · ")
									: "Nothing to fix"
							}}</span>
						</span>
						<span
							v-if="row.late_fees_so_far"
							class="shrink-0 text-sm font-medium text-ink-red-4"
							>{{ formatMoney(row.late_fees_so_far) }} in late fees</span
						>
					</RouterLink>
					<Button
						v-if="data.scores.length > 8 && !showAllScores"
						class="self-start"
						variant="ghost"
						:label="`Show all ${data.scores.length}`"
						@click="showAllScores = true"
					/>
				</section>
				<RecentActivity :entries="data.dashboard.recent" />
			</div>

			<!-- Each area as a card: its colour and icon, then each number on a line of its own with
			     its status, opening the list of what it counts. Zeros stay quiet. -->
			<div class="grid grid-cols-1 gap-4 lg:grid-cols-2" data-tour="overview-areas">
				<section
					v-for="section in busy"
					:key="section.key || section.title"
					class="flex flex-col rounded-xl border border-outline-gray-1"
					:aria-label="section.title"
				>
					<header class="flex items-center gap-3 px-4 pb-2 pt-4">
						<span
							class="flex size-8 shrink-0 items-center justify-center rounded-full"
							:class="kindTint(areaKind(section)).tile"
						>
							<span
								:class="KINDS[areaKind(section)]?.icon || 'lucide-layout-grid'"
								class="size-4"
								aria-hidden="true"
							/>
						</span>
						<h2 class="flex-1 text-base font-semibold text-ink-gray-8">
							{{ section.title }}
						</h2>
						<Badge
							v-if="needingCount(section)"
							theme="red"
							:label="`${needingCount(section)} to look at`"
						/>
					</header>
					<ul class="flex flex-col px-2 pb-2">
						<li v-for="card in section.cards" :key="card.label">
							<component
								:is="opens(card, section.title) ? RouterLink : 'a'"
								v-bind="linkTo(card, section.title)"
								class="flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-surface-gray-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4"
							>
								<span
									class="size-4 shrink-0"
									:class="[
										STATUS_ICONS[card.value ? card.tone : 'gray'] ||
											STATUS_ICONS.gray,
										card.value ? valueClass(card) : 'text-ink-gray-4',
									]"
									aria-hidden="true"
								/>
								<span
									class="flex-1 text-base"
									:class="card.value ? 'text-ink-gray-8' : 'text-ink-gray-5'"
									>{{ card.label }}</span
								>
								<span
									class="text-lg font-semibold tabular-nums"
									:class="valueClass(card)"
									>{{ card.value }}</span
								>
								<span
									class="lucide-chevron-right size-4 shrink-0 text-ink-gray-4"
									aria-hidden="true"
								/>
							</component>
						</li>
					</ul>
				</section>
			</div>

			<p v-if="quiet.length" class="text-sm text-ink-gray-5">
				Nothing recorded yet: {{ quiet.map((section) => section.title).join(" · ") }}.
			</p>
			<p class="text-sm text-ink-gray-5">Each number opens the list of what it counts.</p>
		</template>
	</div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { Badge, Button, Skeleton } from "frappe-ui";
import { BarChart } from "frappe-ui/charts";
import { boot } from "@/boot";
import { call } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import ClientPicker from "@/components/ClientPicker.vue";
import RecentActivity from "@/components/RecentActivity.vue";
import ScoreBadge from "@/components/ScoreBadge.vue";
import UrgencyTiles from "@/components/UrgencyTiles.vue";
import { formatMoney } from "@/lib/format";
import { listRoute } from "@/lib/listFilters";
import { STATUS_ICONS } from "@/lib/status";
import { KINDS } from "@/pages/myWork";
import { kindTint } from "@/lib/areas";
import {
	areaKind,
	isQuiet,
	needingCount,
	needsYou,
	onTimeParts,
	onTimeSummary,
	showPercent,
	valueClass,
} from "@/lib/overview";
import { notLoaded } from "@/offline/reachability";
import { chosenCompanies, loadClients } from "@/stores/clientFilter";

// The series of the two charts, as the server names them.
const DUE_SERIES = ["Filings", "Renewals", "Legal dates"];
const FILED_SERIES = ["On time", "Late", "Not filed"];
const FILED_COLOURS = {
	"On time": { color: "var(--ink-green-4)" },
	Late: { color: "var(--ink-amber-4)" },
	"Not filed": { color: "var(--ink-red-4)" },
};

const firstName = (boot.userFullname || "").split(" ")[0];
const hour = new Date().getHours();
const greeting = `${hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening"}${
	firstName ? `, ${firstName}` : ""
}`;
const today = new Date().toLocaleDateString(undefined, {
	weekday: "long",
	day: "numeric",
	month: "long",
	year: "numeric",
});

const data = ref(null);
const showAllScores = ref(false);
const loading = ref(false);
const error = ref("");

// Each number opens the app's own list of what it counts; a few still open the Desk.
const opens = (card, section) => listRoute(card, section);
const linkTo = (card, section) => {
	const route = opens(card, section);
	return route ? { to: route } : { href: card.link };
};
const parts = computed(() => (data.value ? onTimeParts(data.value.on_time) : []));
const needs = computed(() => needsYou(data.value.sections));
const busy = computed(() => data.value.sections.filter((section) => !isQuiet(section)));
const quiet = computed(() => data.value.sections.filter(isQuiet));

async function load() {
	loading.value = true;
	error.value = "";
	try {
		const params = chosenCompanies.value ? { companies: chosenCompanies.value } : {};
		data.value = await call("kxcompliance.api.overview", params);
	} catch (err) {
		// Numbers already on screen stay; the banner says the server is not answering.
		if (!(err.isNetwork && data.value)) {
			error.value = err.isNetwork ? notLoaded("the overview") : err.message;
		}
	} finally {
		loading.value = false;
	}
}

onMounted(() => loadClients().then(load));
watch(chosenCompanies, load);
</script>
