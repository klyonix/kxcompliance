<template>
	<Dialog v-model:open="open" :title="`Credit ${bill.name}`" :actions="actions">
		<form class="flex flex-col gap-4" @submit.prevent>
			<p class="text-base text-ink-gray-6">
				A credit note lowers what the client owes on this bill, with the GST on it, up to
				the {{ money(bill.outstanding_amount, bill.currency) }} still due. Each line is
				credited once: in full, or for less.
			</p>
			<FormControl v-model="form.line" type="select" label="Credit" :options="lineOptions" />
			<FormControl
				v-if="chosen"
				v-model="form.amount"
				type="number"
				label="Amount before GST"
				:description="`At most ${money(chosen.creditable, bill.currency)}.`"
			/>
			<p v-else class="text-base text-ink-gray-6">
				{{ money(openTotal, bill.currency) }} before GST, on
				{{ openLines.length === 1 ? "1 line" : `${openLines.length} lines` }}.
			</p>
			<FormControl
				v-model="form.reason"
				type="textarea"
				:rows="2"
				label="Reason"
				placeholder="Printed on the credit note, such as a fee agreed lower"
			/>
			<p v-if="problem" role="alert" class="text-sm text-ink-red-4">{{ problem }}</p>
			<p v-if="error" role="alert" class="text-base text-ink-red-4">{{ error }}</p>
		</form>
	</Dialog>
</template>

<script setup>
// A credit note against a sent bill: every line not yet credited, or one line in full or in part.
import { computed, reactive, ref, watch } from "vue";
import { Dialog, FormControl, toast } from "frappe-ui";
import { call } from "@/api";
import { creditProblem, money } from "@/lib/billing";

const props = defineProps({ bill: { type: Object, required: true } });
const emit = defineEmits(["saved"]);
const open = defineModel("open", { type: Boolean, default: false });

const ALL = "all";
const form = reactive({ line: ALL, amount: "", reason: "" });
const error = ref("");
// The actions keep one identity, so the dialog keeps its button busy while saving; and one save
// at a time, so a second click while the first is on its way records nothing twice.
const actions = [{ label: "Make credit note", variant: "solid", onClick: save }];
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

const openLines = computed(() => props.bill.items.filter((line) => Number(line.creditable) > 0));
const openTotal = computed(() =>
	openLines.value.reduce((total, line) => total + Number(line.creditable), 0)
);
// Every line at once only fits while it and its GST are no more than what is still due.
const allFits = computed(() => {
	const net = Number(props.bill.net_total) || 0;
	const withGst = net ? (openTotal.value * Number(props.bill.grand_total)) / net : 0;
	return withGst <= Number(props.bill.outstanding_amount) + 0.005;
});
const lineOptions = computed(() => [
	...(allFits.value ? [{ label: "Every line not yet credited", value: ALL }] : []),
	...openLines.value.map((line) => ({
		label: `${line.description} (${money(line.creditable, props.bill.currency)})`,
		value: line.name,
	})),
]);
// A line's credit is at most what is left on it, and no more than what is still due before GST.
const dueBeforeGst = computed(() => {
	const grand = Number(props.bill.grand_total) || 0;
	const due = Number(props.bill.outstanding_amount) || 0;
	return grand ? Math.floor((due * Number(props.bill.net_total) * 100) / grand) / 100 : due;
});
const chosen = computed(() => {
	const line = openLines.value.find((row) => row.name === form.line);
	return line
		? { ...line, creditable: Math.min(Number(line.creditable), dueBeforeGst.value) }
		: null;
});
const problem = computed(() =>
	checking.value ? creditProblem({ ...form, line: chosen.value }) : null
);

watch(open, (now) => {
	if (!now) return;
	Object.assign(form, { line: allFits.value ? ALL : openLines.value[0]?.name, reason: "" });
	error.value = "";
	checking.value = false;
});

watch(
	() => form.line,
	() => {
		form.amount = chosen.value ? chosen.value.creditable : "";
	},
	{ immediate: true }
);

async function record({ close }) {
	checking.value = true;
	error.value = "";
	if (creditProblem({ ...form, line: chosen.value })) return;
	try {
		const result = await call(
			"kxcompliance.api.credit_bill",
			{
				name: props.bill.name,
				reason: form.reason.trim(),
				...(chosen.value ? { line: chosen.value.name, amount: Number(form.amount) } : {}),
			},
			{ httpMethod: "POST" }
		);
		checking.value = false;
		close();
		toast.success(`Credit note ${result.credit_note} made`);
		emit("saved");
	} catch (err) {
		error.value = err.message;
	}
}
</script>
