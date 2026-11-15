<template>
	<Dialog
		v-model:open="open"
		:title="`Write off what is left on ${bill.name}`"
		:actions="actions"
	>
		<form class="flex flex-col gap-4" @submit.prevent>
			<p class="text-base text-ink-gray-6">
				{{ money(bill.outstanding_amount, bill.currency) }} is still due. Writing it off
				books it as a loss to the firm and the bill is settled; the client is not told.
			</p>
			<FormControl
				v-model="reason"
				type="textarea"
				:rows="2"
				label="Reason"
				placeholder="Such as bank charges the client deducted"
			/>
			<p v-if="error" role="alert" class="text-base text-ink-red-4">{{ error }}</p>
		</form>
	</Dialog>
</template>

<script setup>
// Writing off a small balance a client will not pay on a sent bill, with the reason.
import { ref, watch } from "vue";
import { Dialog, FormControl, toast } from "frappe-ui";
import { call } from "@/api";
import { money } from "@/lib/billing";

const props = defineProps({ bill: { type: Object, required: true } });
const emit = defineEmits(["saved"]);
const open = defineModel("open", { type: Boolean, default: false });

const reason = ref("");
const error = ref("");
// The actions keep one identity, so the dialog keeps its button busy while saving; and one save
// at a time, so a second click while the first is on its way records nothing twice.
const actions = [{ label: "Write off", variant: "solid", theme: "red", onClick: save }];
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

watch(open, (now) => {
	if (!now) return;
	reason.value = "";
	error.value = "";
});

async function record({ close }) {
	error.value = "";
	if (!reason.value.trim()) {
		error.value = "Say why it is written off.";
		return;
	}
	try {
		await call(
			"kxcompliance.api.write_off_bill",
			{ name: props.bill.name, reason: reason.value.trim() },
			{ httpMethod: "POST" }
		);
		close();
		toast.success("Written off");
		emit("saved");
	} catch (err) {
		error.value = err.message;
	}
}
</script>
