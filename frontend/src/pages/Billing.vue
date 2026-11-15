<template>
	<AppPageHeader title="Billing">
		<template #actions>
			<Button
				v-if="isManager() && isMobile"
				icon="lucide-settings"
				aria-label="Billing settings"
				:route="{ name: 'BillingSettings' }"
			/>
			<Button
				v-else-if="isManager()"
				icon-left="lucide-settings"
				label="Settings"
				:route="{ name: 'BillingSettings' }"
			/>
			<Button
				variant="solid"
				icon-left="lucide-plus"
				label="New bill"
				:route="{ name: 'NewBill' }"
			/>
		</template>
	</AppPageHeader>

	<div class="mx-auto flex w-full max-w-5xl flex-col gap-4 px-4 py-6 sm:px-6">
		<ClientPicker />
		<Tabs v-model="section">
			<FormControl
				v-if="isMobile"
				v-model="section"
				type="select"
				:options="SECTIONS"
				aria-label="Show"
			/>
			<TabList v-else class="overflow-x-auto" data-tour="billing-sections">
				<TabTrigger value="bills" label="Bills" icon-left="lucide-receipt" />
				<TabTrigger value="payments" label="Payments" icon-left="lucide-indian-rupee" />
				<TabTrigger value="summary" label="Summary" icon-left="lucide-chart-column" />
			</TabList>
			<TabPanel value="summary" class="data-[state=inactive]:hidden pt-4">
				<BillingSummary />
			</TabPanel>
			<TabPanel value="payments" class="data-[state=inactive]:hidden pt-4">
				<PaymentsList />
			</TabPanel>
			<TabPanel value="bills" class="data-[state=inactive]:hidden flex flex-col gap-4 pt-4">
				<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
					<TabButtons
						v-model="view"
						data-tour="bill-views"
						:options="tabs"
						class="self-start overflow-x-auto"
					/>
					<TextInput
						v-model="search"
						type="search"
						class="sm:w-64"
						placeholder="Search by bill or client"
						aria-label="Search bills"
					/>
				</div>
				<p v-if="counts && dueLine" class="text-base text-ink-gray-6">{{ dueLine }}</p>
				<p v-if="error" role="alert" class="text-base text-ink-red-4">{{ error }}</p>

				<div v-if="loading && !rows.length" class="flex flex-col gap-2" aria-busy="true">
					<Skeleton v-for="index in 5" :key="index" class="h-12 w-full rounded-lg" />
				</div>
				<div
					v-else-if="!rows.length"
					class="flex flex-col items-center gap-2 py-16 text-center"
				>
					<p class="text-lg font-medium text-ink-gray-8">{{ empty.title }}</p>
					<p class="max-w-sm text-base text-ink-gray-5">{{ empty.detail }}</p>
				</div>
				<div v-else class="flex flex-col">
					<div
						class="hidden items-center gap-3 border-b border-outline-gray-1 px-3 pb-2 text-xs font-medium text-ink-gray-5 sm:flex"
						aria-hidden="true"
					>
						<span class="flex-1">Bill</span>
						<span class="w-28">Made</span>
						<span class="w-28">Due</span>
						<span class="w-28 text-right">Total</span>
						<span class="w-28 text-right">Still due</span>
						<span class="w-24">Status</span>
					</div>
					<RouterLink
						v-for="row in rows"
						:key="row.name"
						:to="{ name: 'Bill', params: { name: row.name } }"
						class="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-outline-gray-1 px-3 py-2.5 hover:bg-surface-gray-1"
					>
						<span class="flex min-w-0 flex-1 flex-col">
							<span class="truncate text-base font-medium text-ink-gray-8">{{
								row.name
							}}</span>
							<span class="truncate text-sm text-ink-gray-5">{{
								row.billed_company || row.compliance_client
							}}</span>
						</span>
						<span class="hidden w-28 text-sm text-ink-gray-6 sm:block">{{
							formatDate(row.posting_date)
						}}</span>
						<span class="hidden w-28 text-sm text-ink-gray-6 sm:block">{{
							formatDate(row.due_date)
						}}</span>
						<span class="text-right text-base text-ink-gray-8 sm:w-28">{{
							money(row.rounded_total || row.grand_total, row.currency)
						}}</span>
						<span class="hidden w-28 text-right text-base text-ink-gray-8 sm:block">{{
							row.docstatus === 1 ? money(row.outstanding_amount, row.currency) : "—"
						}}</span>
						<span class="sm:w-24"><Badge v-bind="billState(row)" /></span>
					</RouterLink>
					<ListPager
						v-model:page="page"
						v-model:size="size"
						class="mt-2"
						:total="total"
						:loading="loading"
					/>
				</div>
			</TabPanel>
		</Tabs>
	</div>
</template>

<script setup>
// The firm's bills (drafts to check and send, unpaid ones, paid ones, all; each tab with its count
// and what is still due) and the payments it has received, for one client or every client.
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import {
	Badge,
	Button,
	FormControl,
	Skeleton,
	TabButtons,
	TabList,
	TabPanel,
	TabTrigger,
	Tabs,
	TextInput,
} from "frappe-ui";
import { call } from "@/api";
import { isManager } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import BillingSummary from "@/components/BillingSummary.vue";
import ClientPicker from "@/components/ClientPicker.vue";
import ListPager from "@/components/ListPager.vue";
import PaymentsList from "@/components/PaymentsList.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { useTabQuery } from "@/composables/useTabQuery";
import { BILL_VIEWS, billState, money } from "@/lib/billing";
import { formatDate } from "@/lib/format";
import { savePageSize, savedPageSize } from "@/lib/paging";
import { clientFilter, loadClients } from "@/stores/clientFilter";

const SECTIONS = [
	{ label: "Bills", value: "bills" },
	{ label: "Payments", value: "payments" },
	{ label: "Summary", value: "summary" },
];
const isMobile = useIsMobile();
const section = useTabQuery(
	SECTIONS.map((option) => option.value),
	"bills",
	"show"
);
const view = useTabQuery(BILL_VIEWS.map((option) => option.value));
const search = ref("");
const rows = ref([]);
const total = ref(0);
const counts = ref(null);
const page = ref(1);
const size = ref(savedPageSize("billing"));
const loading = ref(false);
const error = ref("");

const tabs = computed(() =>
	BILL_VIEWS.map((option) => ({
		value: option.value,
		label: counts.value ? `${option.label} ${counts.value[option.value].count}` : option.label,
	}))
);
const dueLine = computed(() => {
	const due = counts.value?.[view.value]?.due;
	return due ? `${money(due)} still due in these bills.` : "";
});
const empty = computed(() => BILL_VIEWS.find((option) => option.value === view.value).empty);

// Only what is set: a GET request would send an empty value as text.
const query = () => {
	const asked = {};
	if (clientFilter.client) asked.client = clientFilter.client;
	if (search.value.trim()) asked.text = search.value.trim();
	return asked;
};

let latest = 0;
async function load() {
	const ticket = ++latest;
	loading.value = true;
	error.value = "";
	try {
		const [found, counted] = await Promise.all([
			call("kxcompliance.api.bills", {
				...query(),
				view: view.value,
				start: (page.value - 1) * size.value,
				page_length: size.value,
			}),
			call("kxcompliance.api.bill_counts", query()),
		]);
		if (ticket !== latest) return;
		rows.value = found.rows;
		total.value = found.total;
		counts.value = counted;
	} catch (err) {
		if (ticket === latest) error.value = err.message;
	} finally {
		if (ticket === latest) loading.value = false;
	}
}

// Another tab, client or search starts from the first page; that page is then read.
function fromFirstPage() {
	if (page.value !== 1) page.value = 1;
	else load();
}

let typing;
watch(search, () => {
	clearTimeout(typing);
	typing = setTimeout(fromFirstPage, 300);
});
watch(view, fromFirstPage);
watch(() => clientFilter.client, fromFirstPage);
watch([page, size], load);
watch(size, (chosen) => savePageSize("billing", chosen));

onMounted(async () => {
	await loadClients();
	load();
});
</script>
