<template>
	<AppPageHeader :title="name" :parent="parent" />

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6 sm:px-6">
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<Skeleton v-else-if="!bill" class="h-64 w-full rounded-lg" />

		<template v-else>
			<section class="flex flex-col gap-2">
				<div class="flex flex-wrap items-center gap-2">
					<Badge :label="state.label" :theme="state.theme" size="md" />
					<span class="text-base text-ink-gray-6">
						{{ bill.customer_name }} · made {{ formatDate(bill.posting_date) }} · due
						{{ formatDate(bill.due_date) }}
					</span>
				</div>
				<p v-if="bill.docstatus === 0" class="text-base text-ink-gray-6">
					A draft: nothing is in the books and the client has not seen it. Check it, then
					send it.
				</p>
			</section>

			<section class="flex flex-col" aria-labelledby="lines-heading">
				<h2 id="lines-heading" class="pb-2 text-base font-semibold text-ink-gray-8">
					Lines
				</h2>
				<div
					v-for="(line, index) in bill.items"
					:key="index"
					class="flex items-start gap-3 border-b border-outline-gray-1 py-2"
				>
					<span class="min-w-0 flex-1 text-base text-ink-gray-8">
						{{ line.description }}
						<RouterLink
							v-if="line.filing"
							:to="{ name: 'ComplianceTask', params: { name: line.filing } }"
							class="ml-1 text-sm text-ink-gray-5 hover:underline"
							>{{ line.filing }}</RouterLink
						>
					</span>
					<span class="text-base text-ink-gray-8">{{
						money(line.amount, bill.currency)
					}}</span>
				</div>
				<dl class="flex flex-col gap-1 pt-3 text-base">
					<div class="flex justify-between text-ink-gray-7">
						<dt>Before GST</dt>
						<dd>{{ money(bill.net_total, bill.currency) }}</dd>
					</div>
					<div
						v-for="tax in bill.taxes"
						:key="tax.description"
						class="flex justify-between text-ink-gray-7"
					>
						<dt>{{ tax.description }}</dt>
						<dd>{{ money(tax.amount, bill.currency) }}</dd>
					</div>
					<div class="flex justify-between font-semibold text-ink-gray-8">
						<dt>Total</dt>
						<dd>{{ money(bill.rounded_total || bill.grand_total, bill.currency) }}</dd>
					</div>
					<div
						v-if="bill.docstatus === 1"
						class="flex justify-between"
						:class="
							Number(bill.outstanding_amount) > 0
								? 'text-ink-red-4'
								: 'text-ink-green-4'
						"
					>
						<dt>Still due</dt>
						<dd>{{ money(bill.outstanding_amount, bill.currency) }}</dd>
					</div>
				</dl>
			</section>

			<section
				v-if="bill.docstatus === 1"
				class="flex flex-col gap-2"
				aria-labelledby="payments-heading"
			>
				<div class="flex items-center justify-between gap-3">
					<h2 id="payments-heading" class="text-base font-semibold text-ink-gray-8">
						Payments
					</h2>
					<Button
						v-if="Number(bill.outstanding_amount) > 0"
						size="sm"
						icon-left="lucide-indian-rupee"
						label="Record payment"
						@click="paying = true"
					/>
				</div>
				<p v-if="!bill.payments.length" class="text-base text-ink-gray-5">
					Nothing received yet.
				</p>
				<div
					v-for="payment in bill.payments"
					:key="payment.name"
					class="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-outline-gray-1 py-2 last:border-b-0"
				>
					<span class="w-24 text-sm text-ink-gray-5">{{
						formatDate(payment.posting_date)
					}}</span>
					<span class="min-w-0 flex-1 text-base text-ink-gray-8">
						{{ payment.mode_of_payment }}
						<span
							v-if="payment.reference_no !== payment.mode_of_payment"
							class="text-sm text-ink-gray-5"
						>
							· {{ payment.reference_no }}</span
						>
						<span v-if="payment.tds" class="text-sm text-ink-gray-5">
							· TDS {{ money(payment.tds, bill.currency) }}</span
						>
					</span>
					<span class="text-base text-ink-gray-8">{{
						money(payment.paid_amount, bill.currency)
					}}</span>
					<Button
						variant="ghost"
						size="sm"
						icon="lucide-file-down"
						:aria-label="`Receipt for the payment of ${formatDate(
							payment.posting_date
						)}`"
						:href="`/api/method/kxcompliance.api.receipt_pdf?name=${encodeURIComponent(
							payment.name
						)}`"
						target="_blank"
					/>
					<Button
						variant="ghost"
						size="sm"
						icon="lucide-undo-2"
						:aria-label="`Cancel the payment of ${formatDate(payment.posting_date)}`"
						@click="undoPayment(payment)"
					/>
				</div>
			</section>

			<p v-if="actionError" role="alert" class="text-base text-ink-red-4">
				{{ actionError }}
			</p>
			<div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
				<Button
					v-if="bill.docstatus !== 2"
					theme="red"
					:label="bill.docstatus === 0 ? 'Delete draft' : 'Cancel bill'"
					:loading="busy === 'cancel'"
					@click="cancel"
				/>
				<Button
					icon-left="lucide-file-down"
					label="PDF"
					:href="`/api/method/kxcompliance.api.bill_pdf?name=${encodeURIComponent(
						name
					)}`"
					target="_blank"
				/>
				<Button
					v-if="bill.docstatus === 0"
					variant="solid"
					icon-left="lucide-send"
					label="Send to client"
					:loading="busy === 'send'"
					@click="send"
				/>
			</div>
		</template>
	</div>
	<PaymentDialog v-if="bill" v-model:open="paying" :bill="bill" @saved="load" />
</template>

<script setup>
// One of the firm's bills: its lines, GST and totals, and sending, the PDF or cancelling it.
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { Badge, Button, Skeleton, dialog, toast } from "frappe-ui";
import { call } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import PaymentDialog from "@/components/PaymentDialog.vue";
import { billState, money } from "@/lib/billing";
import { formatDate } from "@/lib/format";

const props = defineProps({ name: { type: String, required: true } });
const router = useRouter();

const bill = ref(null);
const error = ref("");
const actionError = ref("");
const busy = ref("");
const paying = ref(false);

const state = computed(() => billState(bill.value));
const parent = computed(() =>
	bill.value?.compliance_client
		? {
				label: bill.value.compliance_client,
				route: { name: "Client", params: { name: bill.value.compliance_client } },
		  }
		: { label: "Clients", route: { name: "Clients" } }
);

async function load() {
	error.value = "";
	try {
		bill.value = await call("kxcompliance.api.bill", { name: props.name });
	} catch (err) {
		error.value = err.message;
	}
}

async function act(kind, method, done) {
	actionError.value = "";
	busy.value = kind;
	try {
		const result = await call(method, { name: props.name }, { httpMethod: "POST" });
		await done(result);
	} catch (err) {
		actionError.value = err.message;
	} finally {
		busy.value = "";
	}
}

function send() {
	dialog.confirm({
		title: `Send ${props.name}?`,
		message:
			"It goes into the books and is emailed to the client. A sent bill can only be cancelled, not changed.",
		confirmLabel: "Send",
		onConfirm: () =>
			act("send", "kxcompliance.api.send_bill", async (result) => {
				toast.success(
					result.emailed_to
						? `Sent to ${result.emailed_to}`
						: "Sent; no email address or email account, so it was not emailed"
				);
				await load();
			}),
	});
}

function cancel() {
	const draft = bill.value.docstatus === 0;
	dialog.confirm({
		title: draft ? `Delete draft ${props.name}?` : `Cancel ${props.name}?`,
		message: draft
			? "Its filings can go on another bill."
			: "It is reversed in the books, and its filings can be billed again. This cannot be undone.",
		confirmLabel: draft ? "Delete" : "Cancel bill",
		theme: "red",
		onConfirm: () =>
			act("cancel", "kxcompliance.api.cancel_bill", async () => {
				toast.success(draft ? "Draft deleted" : "Bill cancelled");
				if (draft) router.replace(parent.value.route);
				else await load();
			}),
	});
}

function undoPayment(payment) {
	dialog.confirm({
		title: `Cancel the payment of ${money(payment.paid_amount, bill.value.currency)}?`,
		message: "It is reversed in the books and the bill is due again by that much.",
		confirmLabel: "Cancel payment",
		theme: "red",
		onConfirm: async () => {
			actionError.value = "";
			try {
				await call(
					"kxcompliance.api.cancel_payment",
					{ name: payment.name },
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
