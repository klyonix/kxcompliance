<template>
	<Dialog
		v-model:open="open"
		:title="title"
		:actions="[{ label: 'Save outcome', variant: 'solid', onClick: save }]"
	>
		<form class="flex flex-col gap-4" @submit.prevent>
			<FormControl
				v-model="form.status"
				type="select"
				label="What happened"
				:options="OUTCOME_STATUSES.map((status) => ({ label: status, value: status }))"
			/>
			<FormControl
				v-model="form.attended_by"
				label="Attended by"
				placeholder="Advocate or staff"
			/>
			<FormControl
				v-model="form.proceedings"
				type="textarea"
				label="Proceedings"
				placeholder="What was argued, filed or directed"
				:rows="3"
				:error="
					checking ? proceedingsError(legalDate.kind, form.status, form.proceedings) : ''
				"
			/>
			<FormControl
				v-model="form.next_date"
				type="date"
				:format="pickerFormat()"
				label="Next date"
				:description="nextDateHint"
				:error="nextDateError(legalDate.date, form.next_date) || ''"
			/>
			<p v-if="error" role="alert" class="text-base text-ink-red-4">{{ error }}</p>
		</form>
	</Dialog>
</template>

<script setup>
// What happened at a hearing or deadline, and the next date it was put off to.
import { computed, reactive, ref, watch } from "vue";
import { Dialog, FormControl } from "frappe-ui";
import { formatDate, pickerFormat } from "@/lib/format";
import { OUTCOME_STATUSES, nextDateError, outcomeValues, proceedingsError } from "@/lib/legal";

const props = defineProps({
	legalDate: { type: Object, required: true },
	// Sends the outcome (online, or kept on the device until it can be sent).
	send: { type: Function, required: true },
});
const emit = defineEmits(["saved"]);
const open = defineModel("open", { type: Boolean, default: false });

const form = reactive({ status: "Done", attended_by: "", proceedings: "", next_date: "" });
const checking = ref(false);
const error = ref("");

const title = computed(() => `${props.legalDate.kind}, ${formatDate(props.legalDate.date)}`);
const nextDateHint = computed(() =>
	form.status === "Missed"
		? "When it is listed again, or the new last day; it is added to the dates."
		: "A new hearing or deadline is added on this date."
);

watch(open, (now) => {
	if (!now) return;
	Object.assign(form, { status: "Done", attended_by: "", proceedings: "", next_date: "" });
	checking.value = false;
	error.value = "";
});

async function save({ close }) {
	checking.value = true;
	error.value = "";
	if (
		proceedingsError(props.legalDate.kind, form.status, form.proceedings) ||
		nextDateError(props.legalDate.date, form.next_date)
	) {
		return;
	}
	try {
		await props.send(props.legalDate, outcomeValues(form));
		close();
		emit("saved");
	} catch (err) {
		error.value = err.message;
	}
}
</script>
