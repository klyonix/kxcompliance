<template>
	<p
		v-if="error"
		role="alert"
		class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
	>
		{{ error }}
	</p>
	<div v-else-if="!summary" class="flex flex-col gap-3" aria-busy="true">
		<Skeleton class="h-6 w-1/2 rounded" />
		<Skeleton class="h-32 w-full rounded-lg" />
		<Skeleton class="h-24 w-full rounded-lg" />
	</div>

	<template v-else>
		<section class="flex flex-col gap-3" aria-labelledby="account-heading">
			<div class="flex flex-wrap items-start justify-between gap-3">
				<div class="flex flex-col gap-0.5">
					<h2 id="account-heading" class="text-base font-semibold text-ink-gray-8">
						This financial year
					</h2>
					<p class="text-sm text-ink-gray-5">
						{{ formatDate(summary.year.from_date) }} to
						{{ formatDate(summary.year.to_date) }}
					</p>
				</div>
				<Button
					icon-left="lucide-file-down"
					label="Statement of account"
					@click="statement = true"
				/>
			</div>
			<dl class="grid grid-cols-2 gap-3 sm:grid-cols-4">
				<div
					v-for="fact in facts"
					:key="fact.label"
					class="flex flex-col gap-0.5 rounded-lg bg-surface-gray-1 px-3 py-2.5"
				>
					<dt class="text-sm text-ink-gray-6">{{ fact.label }}</dt>
					<dd class="text-xl font-semibold" :class="FACT_TONE[fact.tone]">
						{{ fact.value }}
					</dd>
					<dd v-if="fact.detail" class="text-sm text-ink-red-4">{{ fact.detail }}</dd>
				</div>
			</dl>
			<p v-if="summary.unbilled_count" class="text-base text-ink-gray-6">
				{{ unbilledLine }}
				<RouterLink
					:to="{ name: 'NewBill', query: { client } }"
					class="font-medium text-ink-gray-8 hover:underline"
					>Bill them</RouterLink
				>
			</p>
		</section>

		<section class="flex flex-col gap-1" aria-labelledby="commitment-heading">
			<h2 id="commitment-heading" class="text-base font-semibold text-ink-gray-8">
				Expected this year
			</h2>
			<p class="pb-1 text-sm text-ink-gray-5">
				Recurring charges for each period in the year, and each filing due in it, at the
				client's rates.
			</p>
			<p v-if="!commitment.length" class="text-base text-ink-gray-5">
				No recurring charges or priced filings this year.
			</p>
			<div
				v-for="line in commitment"
				:key="line.label"
				class="flex items-baseline gap-3 border-b border-outline-gray-1 py-2 last:border-b-0"
			>
				<span class="flex min-w-0 flex-1 flex-col">
					<span class="truncate text-base text-ink-gray-8">{{ line.label }}</span>
					<span class="text-sm text-ink-gray-5">{{ line.detail }}</span>
				</span>
				<span class="text-base text-ink-gray-8">{{ line.amount }}</span>
			</div>
			<p v-if="summary.commitment.unpriced" class="pt-1 text-sm text-ink-amber-5">
				{{ unpricedLine }}
			</p>
		</section>

		<section v-if="ageing.length" class="flex flex-col gap-1" aria-labelledby="ageing-heading">
			<h2 id="ageing-heading" class="pb-1 text-base font-semibold text-ink-gray-8">
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

		<BillingCard :client="client" />

		<section class="flex flex-col gap-1" aria-labelledby="payments-heading">
			<div class="flex items-center justify-between gap-3 pb-1">
				<h2 id="payments-heading" class="text-base font-semibold text-ink-gray-8">
					Payments
				</h2>
				<Button
					v-if="summary.payments.length"
					variant="ghost"
					icon-right="lucide-arrow-right"
					label="All payments"
					@click="seeAllPayments"
				/>
			</div>
			<p v-if="!summary.payments.length" class="text-base text-ink-gray-5">
				No payments yet.
			</p>
			<RouterLink
				v-for="payment in summary.payments"
				:key="payment.name"
				:to="{ name: 'Payment', params: { name: payment.name } }"
				class="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-outline-gray-1 py-2 last:border-b-0 hover:bg-surface-gray-1"
			>
				<span class="flex min-w-0 flex-1 flex-col">
					<span class="truncate text-base text-ink-gray-8">{{
						payment.bills.length ? payment.bills.join(", ") : "Paid ahead"
					}}</span>
					<span class="text-sm text-ink-gray-5">{{
						[formatDate(payment.posting_date), payment.mode_of_payment]
							.filter(Boolean)
							.join(" · ")
					}}</span>
				</span>
				<span class="text-base text-ink-gray-8">{{ money(payment.paid_amount) }}</span>
				<span class="lucide-chevron-right size-4 text-ink-gray-5" aria-hidden="true" />
			</RouterLink>
		</section>

		<section class="flex flex-col gap-1" aria-labelledby="rates-heading">
			<div class="flex items-center justify-between gap-3 pb-1">
				<div class="flex flex-col gap-0.5">
					<h2 id="rates-heading" class="text-base font-semibold text-ink-gray-8">
						Rates
					</h2>
					<p class="text-sm text-ink-gray-5">
						{{
							summary.rate_card
								? `${summary.rate_card} card, with any of the client's own rates`
								: "The client's own rates"
						}}
					</p>
				</div>
				<Button
					v-if="isManager()"
					variant="ghost"
					icon-left="lucide-pencil"
					label="Change"
					:route="{ name: 'ClientEdit', params: { name: client } }"
				/>
			</div>
			<p v-if="!rates.length" class="text-base text-ink-gray-5">No rates set.</p>
			<div
				v-for="rate in rates"
				:key="rate.label"
				class="flex items-baseline gap-3 border-b border-outline-gray-1 py-2 last:border-b-0"
			>
				<span class="min-w-0 flex-1 truncate text-base text-ink-gray-8">{{
					rate.label
				}}</span>
				<span class="text-base text-ink-gray-7">{{ rate.amount }}</span>
			</div>
		</section>

		<StatementDialog v-model:open="statement" :client="client" :year="summary.year" />
	</template>
</template>

<script setup>
// The firm's view of a client's account, on the client's Billing tab: the financial year in
// figures, what it is expected to pay and what is still due, its bills, payments and rates.
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { Button, Skeleton } from "frappe-ui";
import { call } from "@/api";
import { isManager } from "@/boot";
import BillingCard from "@/components/BillingCard.vue";
import StatementDialog from "@/components/StatementDialog.vue";
import { accountFacts, ageingRows, commitmentLines, money, rateLine } from "@/lib/billing";
import { formatDate } from "@/lib/format";
import { notLoaded } from "@/offline/reachability";
import { chooseClient } from "@/stores/clientFilter";

const props = defineProps({ client: { type: String, required: true } });

const FACT_TONE = { red: "text-ink-red-4", amber: "text-ink-amber-4", gray: "text-ink-gray-8" };

const router = useRouter();
const summary = ref(null);
const error = ref("");
const statement = ref(false);

const facts = computed(() => accountFacts(summary.value));
const commitment = computed(() => commitmentLines(summary.value.commitment));
const ageing = computed(() => ageingRows(summary.value.outstanding));
const rates = computed(() => summary.value.rates.map(rateLine));
const unbilledLine = computed(() => {
	const count = summary.value.unbilled_count;
	return `${count} filed ${count === 1 ? "return" : "returns"} not billed yet: ${money(
		summary.value.unbilled_total
	)}.`;
});
const unpricedLine = computed(() => {
	const count = summary.value.commitment.unpriced;
	return `${count} ${count === 1 ? "filing" : "filings"} due this year ${
		count === 1 ? "has" : "have"
	} no rate, so ${count === 1 ? "is" : "are"} not counted.`;
});

function seeAllPayments() {
	chooseClient(props.client);
	router.push({ name: "Billing", query: { show: "payments" } });
}

async function load() {
	error.value = "";
	try {
		summary.value = await call("kxcompliance.api.client_summary", { client: props.client });
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this client's account", "opened") : err.message;
	}
}

watch(() => props.client, load);
onMounted(load);
</script>
