<template>
	<Dialog
		v-model:open="open"
		title="Record an advance"
		:actions="[{ label: 'Record advance', variant: 'solid', onClick: save }]"
	>
		<form class="flex flex-col gap-4" @submit.prevent>
			<p class="text-base text-ink-gray-6">
				Money a client pays before it is billed. It is held for the client and used against
				its next bills as they are sent.
			</p>
			<div class="flex flex-col gap-1.5">
				<span class="text-xs text-ink-gray-5">Client</span>
				<Combobox
					v-model="form.client"
					:options="clientOptions"
					placeholder="Choose a client"
					aria-label="Client"
				/>
			</div>
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
					label="Paid by"
					:options="modes.map((mode) => ({ label: mode, value: mode }))"
				/>
				<FormControl
					v-model="form.reference"
					label="Reference"
					placeholder="UTR, UPI or cheque number"
				/>
			</div>
			<p v-if="problem" role="alert" class="text-sm text-ink-red-4">{{ problem }}</p>
			<p v-if="error" role="alert" class="text-base text-ink-red-4">{{ error }}</p>
		</form>
	</Dialog>
</template>

<script setup>
// An advance a client paid before being billed, used against its next bills.
import { computed, reactive, ref, watch } from "vue";
import { Combobox, Dialog, FormControl, toast } from "frappe-ui";
import { call } from "@/api";
import { advanceProblem } from "@/lib/billing";
import { pickerFormat } from "@/lib/format";
import { isoDate } from "@/lib/obligations";
import { clientFilter } from "@/stores/clientFilter";

const props = defineProps({ modes: { type: Array, required: true } });
const emit = defineEmits(["saved"]);
const open = defineModel("open", { type: Boolean, default: false });

const form = reactive({ client: "", amount: "", paid_on: "", mode: "", reference: "" });
const error = ref("");
const checking = ref(false);

const clientOptions = computed(() =>
	clientFilter.clients.map((row) => ({ label: row.name, value: row.name }))
);
const problem = computed(() => (checking.value ? advanceProblem(form) : null));

watch(open, (now) => {
	if (!now) return;
	Object.assign(form, {
		client: clientFilter.client || "",
		amount: "",
		paid_on: isoDate(new Date()),
		mode: props.modes[0] || "",
		reference: "",
	});
	error.value = "";
	checking.value = false;
});

async function save({ close }) {
	checking.value = true;
	error.value = "";
	if (advanceProblem(form)) return;
	try {
		await call(
			"kxcompliance.api.record_advance",
			{
				client: form.client,
				amount: Number(form.amount),
				paid_on: form.paid_on,
				mode: form.mode,
				reference: form.reference.trim(),
			},
			{ httpMethod: "POST" }
		);
		checking.value = false;
		close();
		toast.success("Advance recorded");
		emit("saved");
	} catch (err) {
		error.value = err.message;
	}
}
</script>
