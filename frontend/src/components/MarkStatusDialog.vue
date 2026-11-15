<template>
	<Dialog
		v-model:open="open"
		:title="`Move ${mark.mark} on`"
		:actions="[
			{ label: 'Save status', variant: 'solid', onClick: ({ close }) => save(close) },
		]"
	>
		<form class="flex flex-col gap-4" @submit.prevent>
			<FormControl
				v-model="form.status"
				type="select"
				label="New status"
				:options="statuses.map((value) => ({ label: value, value }))"
			/>
			<template v-for="field in stage?.fields || []" :key="field.name">
				<FormControl
					v-if="field.date"
					v-model="form[field.name]"
					type="date"
					:format="pickerFormat()"
					:label="field.label"
					:error="needed(field)"
				/>
				<FormControl
					v-else
					v-model="form[field.name]"
					:label="field.label"
					:error="needed(field)"
				/>
			</template>
			<p v-if="stage?.follows" class="text-sm text-ink-gray-6">{{ stage.follows }}</p>
			<div v-if="ending && scheduled.length" class="flex flex-col gap-1">
				<p class="text-base text-ink-amber-4">{{ cancelLine(scheduled.length) }}</p>
				<ul class="flex flex-col gap-0.5 pl-1 text-sm text-ink-gray-6">
					<li v-for="legalDate in scheduled" :key="legalDate.name">
						{{ legalDate.kind }}, {{ formatDate(legalDate.date) }}
					</li>
				</ul>
			</div>
			<p v-if="error" role="alert" class="text-base text-ink-red-4">{{ error }}</p>
		</form>
	</Dialog>
</template>

<script setup>
// A trademark moves to its next stage, with what the registry sent for it.
import { computed, reactive, ref, watch } from "vue";
import { Dialog, FormControl, toast } from "frappe-ui";
import { runMethod } from "@/api";
import { formatDate, pickerFormat } from "@/lib/format";
import {
	ENDED_MARK_STATUSES,
	MARK_STATUSES,
	MARK_STATUS_FIELDS,
	cancelLine,
	markStatusDetails,
	scheduledDates,
} from "@/lib/legal";

const props = defineProps({ mark: { type: Object, required: true } });
const emit = defineEmits(["changed"]);
const open = defineModel("open", { type: Boolean, default: false });

const form = reactive({ status: "" });
const scheduled = ref([]);
const missing = ref([]);
const error = ref("");

const statuses = computed(() => MARK_STATUSES.filter((status) => status !== props.mark.status));
const stage = computed(() => MARK_STATUS_FIELDS[form.status]);
const ending = computed(() => ENDED_MARK_STATUSES.includes(form.status));
// Said after a save was tried, until the field is filled in.
const needed = (field) =>
	missing.value.includes(field.label) && !String(form[field.name] || "").trim()
		? "Needed to mark it Registered"
		: "";

// The next stage along, as a starting choice; what is already recorded is filled in.
function startingStatus() {
	const next = MARK_STATUSES[MARK_STATUSES.indexOf(props.mark.status) + 1];
	return next && !ENDED_MARK_STATUSES.includes(next) ? next : statuses.value[0];
}

watch(open, async (now) => {
	if (!now) return;
	for (const key of Object.keys(form)) delete form[key];
	form.status = startingStatus();
	for (const { fields } of Object.values(MARK_STATUS_FIELDS)) {
		for (const field of fields) form[field.name] = props.mark[field.name] || "";
	}
	missing.value = [];
	error.value = "";
	try {
		scheduled.value = await scheduledDates("Trademark", props.mark.name);
	} catch {
		// The list is only shown; the server cancels the dates whether or not it is.
		scheduled.value = [];
	}
});

async function save(close) {
	error.value = "";
	const { details, missing: notGiven } = markStatusDetails(form.status, form);
	missing.value = notGiven;
	if (notGiven.length) return;
	try {
		await runMethod("Trademark", props.mark.name, "change_status", {
			status: form.status,
			details,
		});
		close();
		toast.success(`Now ${form.status}`);
		emit("changed");
	} catch (err) {
		error.value = err.isNetwork
			? "Changing the status needs a connection to the server. Try again when you are back online."
			: err.message;
	}
}
</script>
