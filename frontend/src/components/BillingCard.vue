<template>
	<section
		v-if="billing && (!own || billing.bills.length)"
		class="flex flex-col gap-2"
		aria-labelledby="billing-heading"
	>
		<div class="flex items-center justify-between gap-3">
			<h2 id="billing-heading" class="text-base font-semibold text-ink-gray-8">
				{{ own ? t("Bills from your firm") : "Bills" }}
			</h2>
			<Button
				v-if="own && billing.year"
				icon-left="lucide-file-down"
				:label="t('Statement of account')"
				@click="statement = true"
			/>
			<Button
				v-if="!own && billing.bills.length"
				variant="ghost"
				icon-right="lucide-arrow-right"
				label="All bills"
				@click="seeAll"
			/>
		</div>
		<p
			v-if="own"
			class="text-base"
			:class="billing.overdue ? 'font-medium text-ink-red-4' : 'text-ink-gray-7'"
		>
			{{ balanceLine }}
		</p>
		<p v-if="!billing.bills.length" class="text-base text-ink-gray-5">
			{{ t("No bills yet.") }}
		</p>
		<component
			:is="own ? 'a' : RouterLink"
			v-for="bill in billing.bills"
			:key="bill.name"
			v-bind="
				own
					? { href: pdfLink(bill.name), target: '_blank' }
					: { to: { name: 'Bill', params: { name: bill.name } } }
			"
			class="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-outline-gray-1 py-2 last:border-b-0 hover:bg-surface-gray-1"
		>
			<span class="flex min-w-0 flex-1 flex-col">
				<span class="truncate text-base text-ink-gray-8">{{ bill.name }}</span>
				<span class="text-sm text-ink-gray-5">{{ formatDate(bill.posting_date) }}</span>
			</span>
			<span class="text-base text-ink-gray-8">{{
				money(bill.rounded_total || bill.grand_total, bill.currency)
			}}</span>
			<Badge :label="t(billState(bill).label)" :theme="billState(bill).theme" />
			<span
				v-if="own"
				class="lucide-file-down size-4 text-ink-gray-5"
				:aria-label="t('PDF')"
			/>
		</component>
		<StatementDialog
			v-if="own && billing.year"
			v-model:open="statement"
			:client="client"
			:year="billing.year"
			own
		/>
	</section>
</template>

<script setup>
// A client's bills and balance: on the client's Billing tab, for those who bill, with what it has
// not billed yet; on the client's own home, the bills sent to it, each opening as a PDF, and its
// statement of account.
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { Badge, Button } from "frappe-ui";
import { call } from "@/api";
import StatementDialog from "@/components/StatementDialog.vue";
import { billState, money } from "@/lib/billing";
import { formatDate } from "@/lib/format";
import { t } from "@/lib/i18n";
import { chooseClient } from "@/stores/clientFilter";

const props = defineProps({
	client: { type: String, required: true },
	// The client's own login, rather than the firm.
	own: { type: Boolean, default: false },
});
const router = useRouter();
const billing = ref(null);
const statement = ref(false);

const balanceLine = computed(() => {
	const { outstanding, overdue } = billing.value;
	if (!outstanding) return t("Nothing due.");
	return overdue
		? t("{0} due, {1} of it overdue.", money(outstanding), money(overdue))
		: t("{0} due.", money(outstanding));
});
const pdfLink = (name) => `/api/method/kxcompliance.api.bill_pdf?name=${encodeURIComponent(name)}`;

function seeAll() {
	chooseClient(props.client);
	router.push({ name: "Billing", query: { tab: "all" } });
}

async function load() {
	try {
		billing.value = await call("kxcompliance.api.client_billing", { client: props.client });
	} catch {
		// Billing is extra on this page; without it the rest of the client still shows.
		billing.value = null;
	}
}

watch(() => props.client, load);
onMounted(load);
</script>
