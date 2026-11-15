<template>
	<p
		v-if="error"
		role="alert"
		class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
	>
		{{ error }}
	</p>
	<div v-else-if="!summary" class="flex flex-col gap-3" aria-busy="true">
		<Skeleton class="h-24 w-full rounded-lg" />
		<Skeleton class="h-40 w-full rounded-lg" />
	</div>

	<div v-else class="flex flex-col gap-8">
		<section class="flex flex-col gap-3" aria-labelledby="summary-year-heading">
			<div class="flex flex-col gap-0.5">
				<h2 id="summary-year-heading" class="text-base font-semibold text-ink-gray-8">
					This financial year
				</h2>
				<p class="text-sm text-ink-gray-5">
					{{ formatDate(summary.year.from_date) }} to
					{{ formatDate(summary.year.to_date) }} ·
					{{ clientFilter.client || "every client" }}
				</p>
			</div>
			<dl class="grid grid-cols-2 gap-3 sm:grid-cols-3">
				<div
					v-for="fact in facts"
					:key="fact.label"
					class="flex flex-col gap-0.5 rounded-lg bg-surface-gray-1 px-3 py-2.5"
				>
					<dt class="text-sm text-ink-gray-6">{{ fact.label }}</dt>
					<dd
						class="text-xl font-semibold"
						:class="fact.tone === 'red' ? 'text-ink-red-4' : 'text-ink-gray-8'"
					>
						{{ fact.value }}
					</dd>
					<dd v-if="fact.detail" class="text-sm text-ink-red-4">{{ fact.detail }}</dd>
				</div>
			</dl>
		</section>

		<section
			v-if="ageing.length"
			class="flex flex-col gap-1"
			aria-labelledby="summary-ageing-heading"
		>
			<h2 id="summary-ageing-heading" class="pb-1 text-base font-semibold text-ink-gray-8">
				Still due, by how late
			</h2>
			<div
				v-for="row in ageing"
				:key="row.key"
				class="flex items-baseline gap-3 border-b border-outline-gray-1 py-2 last:border-b-0"
			>
				<span
					class="flex-1 text-base"
					:class="row.key === 'not_due' ? 'text-ink-gray-7' : 'text-ink-red-4'"
					>{{ row.label }}</span
				>
				<span class="text-base text-ink-gray-8">{{ row.amount }}</span>
			</div>
		</section>

		<section class="flex flex-col gap-1" aria-labelledby="summary-months-heading">
			<div class="flex flex-col gap-0.5 pb-1">
				<h2 id="summary-months-heading" class="text-base font-semibold text-ink-gray-8">
					Month by month
				</h2>
				<p class="text-sm text-ink-gray-5">
					Bills sent each month, with GST; the darker part of each bar is settled: paid,
					credited or written off.
				</p>
			</div>
			<p v-if="!summary.by_month.length" class="text-base text-ink-gray-5">
				Nothing billed this year yet.
			</p>
			<div
				v-for="month in summary.by_month"
				:key="month.month_name"
				class="flex flex-col gap-1 border-b border-outline-gray-1 py-2 last:border-b-0"
			>
				<div class="flex flex-wrap items-baseline gap-x-3">
					<span class="w-24 text-base text-ink-gray-8">{{ month.month_name }}</span>
					<span class="flex-1 text-sm text-ink-gray-5">
						{{ month.bills }} {{ month.bills === 1 ? "bill" : "bills" }} ·
						{{ money(month.settled) }} settled
						<template v-if="month.still_due > 0">
							· {{ money(month.still_due) }} due</template
						>
					</span>
					<span class="text-base text-ink-gray-8">{{ money(month.total) }}</span>
				</div>
				<div
					class="h-1.5 overflow-hidden rounded-full bg-surface-gray-2"
					role="img"
					:aria-label="`${money(month.settled)} of ${money(month.total)} settled`"
				>
					<div
						class="h-full rounded-full bg-surface-gray-4"
						:style="{ width: `${barWidth(month.total, summary.by_month)}%` }"
					>
						<div
							class="h-full rounded-full bg-surface-gray-7"
							:style="{ width: `${barWidth(month.settled, [month])}%` }"
						/>
					</div>
				</div>
			</div>
		</section>

		<section
			v-if="!clientFilter.client && summary.owing_most.length"
			class="flex flex-col gap-1"
			aria-labelledby="summary-owing-heading"
		>
			<h2 id="summary-owing-heading" class="pb-1 text-base font-semibold text-ink-gray-8">
				Clients owing most
			</h2>
			<RouterLink
				v-for="line in summary.owing_most"
				:key="line.client"
				:to="{ name: 'Client', params: { name: line.client }, query: { tab: 'billing' } }"
				class="flex items-baseline gap-3 border-b border-outline-gray-1 py-2 last:border-b-0 hover:bg-surface-gray-1"
			>
				<span class="flex min-w-0 flex-1 flex-col">
					<span class="truncate text-base text-ink-gray-8">{{ line.client }}</span>
					<span
						class="text-sm"
						:class="lateOf(line) > 0 ? 'text-ink-red-4' : 'text-ink-gray-5'"
					>
						{{ line.bills }} {{ line.bills === 1 ? "bill" : "bills" }}
						<template v-if="lateOf(line) > 0">
							· {{ money(lateOf(line)) }} overdue</template
						>
					</span>
				</span>
				<span class="text-base text-ink-gray-8">{{ money(line.outstanding) }}</span>
			</RouterLink>
		</section>

		<section class="flex flex-col gap-1" aria-labelledby="summary-unbilled-heading">
			<div class="flex flex-col gap-0.5 pb-1">
				<h2 id="summary-unbilled-heading" class="text-base font-semibold text-ink-gray-8">
					Filed, not billed yet
				</h2>
				<p class="text-sm text-ink-gray-5">
					{{
						summary.unbilled.count
							? `${summary.unbilled.count} filed ${
									summary.unbilled.count === 1 ? "return" : "returns"
							  } with a rate, on no bill: ${money(summary.unbilled.total)}.`
							: "Every filed return with a rate is billed or on a draft."
					}}
				</p>
			</div>
			<div
				v-for="line in summary.unbilled.clients"
				:key="line.client"
				class="flex items-center gap-3 border-b border-outline-gray-1 py-2 last:border-b-0"
			>
				<span class="flex min-w-0 flex-1 flex-col">
					<span class="truncate text-base text-ink-gray-8">{{ line.client }}</span>
					<span class="text-sm text-ink-gray-5"
						>{{ line.count }} {{ line.count === 1 ? "return" : "returns" }}</span
					>
				</span>
				<span class="text-base text-ink-gray-8">{{ money(line.total) }}</span>
				<Button
					size="sm"
					label="Bill"
					:route="{ name: 'NewBill', query: { client: line.client } }"
				/>
			</div>
		</section>
	</div>
</template>

<script setup>
// Billing's Summary tab: the firm's year for every client, or the one chosen at the top.
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { Button, Skeleton } from "frappe-ui";
import { call } from "@/api";
import { ageingRows, barWidth, money, summaryFacts } from "@/lib/billing";
import { formatDate } from "@/lib/format";
import { notLoaded } from "@/offline/reachability";
import { clientFilter } from "@/stores/clientFilter";

const summary = ref(null);
const error = ref("");

const facts = computed(() => summaryFacts(summary.value));
const ageing = computed(() => ageingRows(summary.value.ageing));
const lateOf = (line) => Number(line.outstanding) - Number(line.not_due);

async function load() {
	error.value = "";
	summary.value = null;
	try {
		summary.value = await call(
			"kxcompliance.api.billing_summary",
			clientFilter.client ? { client: clientFilter.client } : {}
		);
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("the billing summary", "opened") : err.message;
	}
}

watch(() => clientFilter.client, load);
onMounted(load);
</script>
