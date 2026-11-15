<template>
	<Dialog
		v-model:open="open"
		:title="title"
		:actions="[{ label: moving ? 'Move' : 'Add date', variant: 'solid', onClick: save }]"
	>
		<form class="flex flex-col gap-4" @submit.prevent>
			<FormControl
				v-if="!moving"
				v-model="form.kind"
				type="select"
				label="What it is"
				:options="DATE_KINDS[doctype].map((kind) => ({ label: kind, value: kind }))"
			/>
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_9rem]">
				<FormControl
					v-model="form.date"
					type="date"
					:format="pickerFormat()"
					:label="moving ? 'New date' : 'Date'"
					:error="missing && !form.date ? 'Pick the date' : ''"
				/>
				<FormControl v-model="form.time" type="time" label="Time" />
			</div>
			<FormControl
				v-model="form.purpose"
				label="Purpose"
				placeholder="Final arguments, reply to the SCN"
			/>
			<p v-if="error" role="alert" class="text-base text-ink-red-4">{{ error }}</p>
		</form>
	</Dialog>
</template>

<script setup>
// A hearing or deadline added by hand, or a scheduled one moved before it happens.
import { computed, reactive, ref, watch } from "vue";
import { Dialog, FormControl } from "frappe-ui";
import { createDoc } from "@/api";
import { formatDate, pickerFormat } from "@/lib/format";
import { DATE_KINDS, moveValues, newDateValues } from "@/lib/legal";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, required: true },
	// The date being moved; none when adding one.
	legalDate: { type: Object, default: null },
	// Sends a change to a date (online, or kept on the device until it can be sent).
	send: { type: Function, required: true },
});
const emit = defineEmits(["saved"]);
const open = defineModel("open", { type: Boolean, default: false });

const form = reactive({ kind: "Hearing", date: "", time: "", purpose: "" });
const missing = ref(false);
const error = ref("");

const moving = computed(() => Boolean(props.legalDate));
const title = computed(() =>
	moving.value
		? `Move ${props.legalDate.kind.toLowerCase()} of ${formatDate(props.legalDate.date)}`
		: "Add a date"
);

watch(open, (now) => {
	if (!now) return;
	const current = props.legalDate;
	Object.assign(form, {
		kind: current?.kind || "Hearing",
		date: current?.date || "",
		time: (current?.time || "").slice(0, 5),
		purpose: current?.purpose || "",
	});
	missing.value = false;
	error.value = "";
});

async function save({ close }) {
	missing.value = true;
	error.value = "";
	if (!form.date) return;
	try {
		if (moving.value) {
			const changes = moveValues(props.legalDate, form);
			if (changes) await props.send(props.legalDate, changes);
		} else {
			await createDoc("Legal Date", newDateValues(props.doctype, props.name, form));
		}
		close();
		emit("saved", moving.value ? "Date moved" : "Date added");
	} catch (err) {
		error.value = err.isNetwork
			? "This needs a connection to the server. Try again when you are back online."
			: err.message;
	}
}
</script>
