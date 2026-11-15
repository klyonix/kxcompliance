<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
			<TextInput
				v-model="search"
				type="search"
				class="sm:w-64"
				placeholder="Search by client or reference"
				aria-label="Search payments"
			/>
			<Button
				icon-left="lucide-plus"
				label="Record advance"
				data-tour="record-advance"
				@click="advancing = true"
			/>
		</div>
		<p v-if="total" class="text-base text-ink-gray-6">
			{{ total === 1 ? "1 payment" : `${total} payments` }} received,
			{{ money(received) }} in all.
		</p>
		<p v-if="error" role="alert" class="text-base text-ink-red-4">{{ error }}</p>

		<div v-if="loading && !rows.length" class="flex flex-col gap-2" aria-busy="true">
			<Skeleton v-for="index in 5" :key="index" class="h-12 w-full rounded-lg" />
		</div>
		<div v-else-if="!rows.length" class="flex flex-col items-center gap-2 py-16 text-center">
			<p class="text-lg font-medium text-ink-gray-8">No payments yet</p>
			<p class="max-w-sm text-base text-ink-gray-5">
				Payments recorded against bills, and advances clients pay ahead, appear here.
			</p>
		</div>
		<div v-else class="flex flex-col">
			<div
				class="hidden grid-cols-[6rem_1fr_10rem_7rem_4rem] items-center gap-3 border-b border-outline-gray-1 px-3 pb-2 text-xs font-medium text-ink-gray-5 sm:grid"
				aria-hidden="true"
			>
				<span>Received</span>
				<span>Client</span>
				<span>For</span>
				<span class="text-right">Amount</span>
				<span />
			</div>
			<div
				v-for="row in rows"
				:key="row.name"
				class="grid grid-cols-[1fr_auto_auto] items-center gap-x-3 gap-y-1 border-b border-outline-gray-1 px-3 py-2.5 sm:grid-cols-[6rem_1fr_10rem_7rem_4rem]"
			>
				<span class="hidden text-sm text-ink-gray-6 sm:block">{{
					formatDate(row.posting_date)
				}}</span>
				<span class="flex min-w-0 flex-col">
					<RouterLink
						:to="{ name: 'Payment', params: { name: row.name } }"
						class="truncate text-base font-medium text-ink-gray-8 hover:underline"
						>{{ row.client || row.party_name }}</RouterLink
					>
					<span class="truncate text-sm text-ink-gray-5">
						<span class="sm:hidden">{{ formatDate(row.posting_date) }} · </span>
						{{ row.mode_of_payment }}
						<template
							v-if="row.reference_no && row.reference_no !== row.mode_of_payment"
						>
							· {{ row.reference_no }}</template
						>
						<template v-if="row.tds > 0"> · TDS {{ money(row.tds) }}</template>
					</span>
				</span>
				<span
					class="order-last col-span-3 flex flex-wrap gap-x-2 text-sm sm:order-none sm:col-span-1"
				>
					<RouterLink
						v-for="name in row.bills"
						:key="name"
						:to="{ name: 'Bill', params: { name } }"
						class="text-ink-gray-7 hover:underline"
						>{{ name }}</RouterLink
					>
					<span v-if="row.unallocated_amount > 0" class="text-ink-amber-4">
						{{ money(row.unallocated_amount) }} held ahead
					</span>
				</span>
				<span class="text-right text-base text-ink-gray-8">{{
					money(row.paid_amount)
				}}</span>
				<span class="flex justify-end">
					<Button
						variant="ghost"
						size="sm"
						icon="lucide-file-down"
						:aria-label="`Receipt for ${row.name}`"
						:href="`/api/method/kxcompliance.api.receipt_pdf?name=${encodeURIComponent(
							row.name
						)}`"
						target="_blank"
					/>
					<Button
						v-if="!row.bills.length"
						variant="ghost"
						size="sm"
						icon="lucide-undo-2"
						:aria-label="`Cancel the advance ${row.name}`"
						@click="undoAdvance(row)"
					/>
				</span>
			</div>
			<ListPager
				v-model:page="page"
				v-model:size="size"
				class="mt-2"
				:total="total"
				:loading="loading"
			/>
		</div>
		<AdvanceDialog v-model:open="advancing" :modes="modes" @saved="load" />
	</div>
</template>

<script setup>
// The payments the firm has received, newest first: against bills, and advances held ahead; for
// one client or every client.
import { onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { Button, Skeleton, TextInput, dialog, toast } from "frappe-ui";
import { call } from "@/api";
import AdvanceDialog from "@/components/AdvanceDialog.vue";
import ListPager from "@/components/ListPager.vue";
import { money } from "@/lib/billing";
import { formatDate } from "@/lib/format";
import { savePageSize, savedPageSize } from "@/lib/paging";
import { clientFilter } from "@/stores/clientFilter";

const search = ref("");
const rows = ref([]);
const total = ref(0);
const received = ref(0);
const modes = ref([]);
const page = ref(1);
const size = ref(savedPageSize("payments"));
const loading = ref(false);
const error = ref("");
const advancing = ref(false);

let latest = 0;
async function load() {
	const ticket = ++latest;
	loading.value = true;
	error.value = "";
	// Only what is set: a GET request would send an empty value as text.
	const asked = { start: (page.value - 1) * size.value, page_length: size.value };
	if (clientFilter.client) asked.client = clientFilter.client;
	if (search.value.trim()) asked.text = search.value.trim();
	try {
		const found = await call("kxcompliance.api.payments", asked);
		if (ticket !== latest) return;
		rows.value = found.rows;
		total.value = found.total;
		received.value = found.received;
		modes.value = found.modes;
	} catch (err) {
		if (ticket === latest) error.value = err.message;
	} finally {
		if (ticket === latest) loading.value = false;
	}
}

function undoAdvance(row) {
	dialog.confirm({
		title: `Cancel the advance of ${money(row.paid_amount)}?`,
		message:
			"It is reversed in the books; bills it was used against are due again by that much.",
		confirmLabel: "Cancel advance",
		theme: "red",
		onConfirm: async () => {
			error.value = "";
			try {
				await call(
					"kxcompliance.api.cancel_payment",
					{ name: row.name },
					{ httpMethod: "POST" }
				);
				toast.success("Advance cancelled");
				await load();
			} catch (err) {
				error.value = err.message;
			}
		},
	});
}

// Another client or search starts from the first page; that page is then read.
function fromFirstPage() {
	if (page.value !== 1) page.value = 1;
	else load();
}

let typing;
watch(search, () => {
	clearTimeout(typing);
	typing = setTimeout(fromFirstPage, 300);
});
watch(() => clientFilter.client, fromFirstPage);
watch([page, size], load);
watch(size, (chosen) => savePageSize("payments", chosen));

onMounted(load);
</script>
