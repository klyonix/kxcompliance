<template>
	<AppPageHeader :title="name" :parent="parent">
		<template v-if="payment && payment.docstatus === 1" #actions>
			<Button
				v-bind="isMobile ? { icon: 'lucide-file-down' } : { iconLeft: 'lucide-file-down' }"
				:label="isMobile ? undefined : 'Receipt'"
				:aria-label="isMobile ? 'Receipt PDF' : undefined"
				:href="receiptLink"
				target="_blank"
			/>
			<Button
				v-bind="isMobile ? { icon: 'lucide-mail' } : { iconLeft: 'lucide-mail' }"
				:label="isMobile ? undefined : 'Email receipt'"
				:aria-label="isMobile ? 'Email receipt' : undefined"
				:loading="busy === 'email'"
				@click="email"
			/>
		</template>
	</AppPageHeader>

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6 sm:px-6">
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<Skeleton v-else-if="!payment" class="h-64 w-full rounded-lg" />

		<template v-else>
			<section class="flex flex-col gap-2" data-tour="payment-state">
				<div class="flex flex-wrap items-center gap-2">
					<Badge
						:label="payment.docstatus === 2 ? 'Cancelled' : 'Received'"
						:theme="payment.docstatus === 2 ? 'red' : 'green'"
						size="md"
					/>
					<span class="text-base text-ink-gray-6">{{ received }}</span>
				</div>
				<p v-if="payment.paid_by_company" class="text-sm text-ink-gray-5">
					Paid from {{ payment.paid_by_company }}.
				</p>
				<p v-if="payment.emailed" class="text-sm text-ink-gray-5">
					{{
						payment.emailed === 1
							? "The receipt has been emailed once."
							: `The receipt has been emailed ${payment.emailed} times.`
					}}
				</p>
			</section>

			<dl class="grid grid-cols-2 gap-3 sm:grid-cols-4">
				<div
					v-for="fact in facts"
					:key="fact.label"
					class="flex flex-col gap-0.5 rounded-lg bg-surface-gray-1 px-3 py-2.5"
				>
					<dt class="text-sm text-ink-gray-6">{{ fact.label }}</dt>
					<dd class="text-lg font-semibold text-ink-gray-8">{{ fact.value }}</dd>
				</div>
			</dl>

			<section class="flex flex-col gap-2" aria-labelledby="settled-heading">
				<h2 id="settled-heading" class="text-base font-semibold text-ink-gray-8">
					Bills it settled
				</h2>
				<p v-if="!payment.bills.length" class="text-base text-ink-gray-5">
					None yet: it is held as an advance and used against the client's next bills as
					they are sent.
				</p>
				<RouterLink
					v-for="row in payment.bills"
					:key="row.name"
					:to="{ name: 'Bill', params: { name: row.name } }"
					class="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-outline-gray-1 py-2 last:border-b-0 hover:bg-surface-gray-1"
				>
					<span class="flex min-w-0 flex-1 flex-col">
						<span class="truncate text-base text-ink-gray-8">{{ row.name }}</span>
						<span class="text-sm text-ink-gray-5">{{ billLine(row) }}</span>
					</span>
					<span class="text-base text-ink-gray-8">{{
						money(row.allocated, payment.currency)
					}}</span>
					<span class="lucide-chevron-right size-4 text-ink-gray-5" aria-hidden="true" />
				</RouterLink>
				<p v-if="payment.unallocated_amount > 0" class="text-base text-ink-amber-5">
					{{ money(payment.unallocated_amount, payment.currency) }} is still held ahead
					for the client's next bills.
				</p>
			</section>

			<p v-if="actionError" role="alert" class="text-base text-ink-red-4">
				{{ actionError }}
			</p>
			<div v-if="payment.docstatus === 1" class="flex justify-end">
				<Button theme="red" label="Cancel payment" @click="cancel" />
			</div>
		</template>
	</div>
</template>

<script setup>
// One payment the firm received: from whom, when and how, TDS, the bills it settled or the
// advance still held; its receipt as a PDF or by email, and cancelling it.
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { Badge, Button, Skeleton, dialog, toast } from "frappe-ui";
import { call } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { money, paymentFacts } from "@/lib/billing";
import { formatDate } from "@/lib/format";

const props = defineProps({ name: { type: String, required: true } });

const isMobile = useIsMobile();
const payment = ref(null);
const error = ref("");
const actionError = ref("");
const busy = ref("");

const parent = computed(() =>
	payment.value?.client
		? {
				label: payment.value.client,
				route: {
					name: "Client",
					params: { name: payment.value.client },
					query: { tab: "billing" },
				},
		  }
		: { label: "Payments", route: { name: "Billing", query: { show: "payments" } } }
);
const received = computed(() =>
	[
		payment.value.client || payment.value.party_name,
		`received ${formatDate(payment.value.posting_date)}`,
	].join(" · ")
);
const facts = computed(() => paymentFacts(payment.value));
const receiptLink = computed(
	() => `/api/method/kxcompliance.api.receipt_pdf?name=${encodeURIComponent(props.name)}`
);
const billLine = (row) =>
	[
		`Made ${formatDate(row.posting_date)}`,
		`total ${money(row.total, payment.value.currency)}`,
		row.still_due > 0 ? `${money(row.still_due, payment.value.currency)} still due` : "paid",
	].join(" · ");

async function load() {
	error.value = "";
	try {
		payment.value = await call("kxcompliance.api.payment", { name: props.name });
	} catch (err) {
		error.value = err.message;
	}
}

async function email() {
	actionError.value = "";
	busy.value = "email";
	try {
		const { emailed_to: to } = await call(
			"kxcompliance.api.email_receipt",
			{ name: props.name },
			{ httpMethod: "POST" }
		);
		toast.success(`Receipt emailed to ${to}`);
		await load();
	} catch (err) {
		actionError.value = err.message;
	} finally {
		busy.value = "";
	}
}

function cancel() {
	dialog.confirm({
		title: `Cancel the payment of ${money(
			payment.value.paid_amount,
			payment.value.currency
		)}?`,
		message: payment.value.bills.length
			? "It is reversed in the books and the bills it settled are due again by that much."
			: "It is reversed in the books; bills it was used against are due again by that much.",
		confirmLabel: "Cancel payment",
		theme: "red",
		onConfirm: async () => {
			actionError.value = "";
			try {
				await call(
					"kxcompliance.api.cancel_payment",
					{ name: props.name },
					{ httpMethod: "POST" }
				);
				toast.success("Payment cancelled");
				await load();
			} catch (err) {
				actionError.value = err.message;
			}
		},
	});
}

watch(() => props.name, load);
onMounted(load);
</script>
