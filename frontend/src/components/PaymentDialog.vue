<template>
	<Dialog
		v-model:open="open"
		:title="`Record a payment against ${bill.name}`"
		:actions="actions"
	>
		<form class="flex flex-col gap-4" @submit.prevent>
			<p class="text-base text-ink-gray-6">
				{{ money(bill.outstanding_amount, bill.currency) }} is still due. A part payment
				leaves the rest due.
			</p>
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
				<FormControl v-model="form.amount" type="number" label="Amount received" />
				<FormControl
					v-model="form.paid_on"
					type="date"
					:format="pickerFormat()"
					label="Received on"
				/>
			</div>
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
				<FormControl
					v-model="form.mode"
					type="select"
					label="Payment mode"
					:options="bill.modes.map((mode) => ({ label: mode, value: mode }))"
				/>
				<FormControl
					v-model="form.reference"
					label="Reference"
					placeholder="UTR, UPI or cheque number"
				/>
			</div>
			<FormControl
				v-if="bill.companies.length > 1"
				v-model="form.paid_by"
				type="select"
				label="Paid from"
				:options="bill.companies.map((name) => ({ label: name, value: name }))"
				description="Any of the client's companies may pay this bill."
			/>
			<FormControl
				v-model="form.tds"
				type="number"
				label="TDS deducted by the client"
				placeholder="0"
				description="Counts towards the bill; claim it against the TDS certificate."
			/>
			<p v-if="problem" role="alert" class="text-sm text-ink-red-4">{{ problem }}</p>
			<p v-if="error" role="alert" class="text-base text-ink-red-4">{{ error }}</p>
		</form>
	</Dialog>
</template>

<script setup>
// A payment received against a sent bill, in full or in part, with any TDS the client deducted.
import { computed, reactive, ref, watch } from "vue";
import { Dialog, FormControl, toast } from "frappe-ui";
import { call } from "@/api";
import { modeForReference, money, paymentProblem } from "@/lib/billing";
import { pickerFormat } from "@/lib/format";
import { isoDate } from "@/lib/obligations";

const props = defineProps({ bill: { type: Object, required: true } });
const emit = defineEmits(["saved"]);
const open = defineModel("open", { type: Boolean, default: false });

const form = reactive({ amount: "", paid_on: "", mode: "", reference: "", tds: "", paid_by: "" });
const error = ref("");
// The actions keep one identity, so the dialog keeps its button busy while saving; and one save
// at a time, so a second click while the first is on its way records nothing twice.
const actions = [{ label: "Record payment", variant: "solid", onClick: save }];
const saving = ref(false);
async function save(args) {
	if (saving.value) return;
	saving.value = true;
	try {
		await record(args);
	} finally {
		saving.value = false;
	}
}
const checking = ref(false);

const problem = computed(() =>
	checking.value ? paymentProblem(form, props.bill.outstanding_amount) : null
);

watch(open, (now) => {
	if (!now) return;
	Object.assign(form, {
		amount: props.bill.outstanding_amount,
		paid_on: isoDate(new Date()),
		mode: props.bill.modes[0],
		reference: "",
		tds: "",
		paid_by: props.bill.billed_company || "",
	});
	error.value = "";
	checking.value = false;
});

async function record({ close }) {
	checking.value = true;
	error.value = "";
	if (paymentProblem(form, props.bill.outstanding_amount)) return;
	try {
		await call(
			"kxcompliance.api.record_payment",
			{
				name: props.bill.name,
				amount: Number(form.amount),
				paid_on: form.paid_on,
				mode: form.mode,
				reference: form.reference.trim(),
				tds: Number(form.tds) || 0,
				paid_by: form.paid_by || null,
			},
			{ httpMethod: "POST" }
		);
		// Saved: the bill's new balance must not be checked against what was just recorded.
		checking.value = false;
		close();
		toast.success("Payment recorded");
		emit("saved");
	} catch (err) {
		error.value = err.message;
	}
}
// A reference typed against Cash means it was not cash.
watch(
	() => form.reference,
	(reference) => {
		form.mode = modeForReference(reference, props.bill.modes || [], form.mode);
	}
);
</script>
