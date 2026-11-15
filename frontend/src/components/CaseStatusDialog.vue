<template>
	<Dialog
		v-model:open="open"
		:title="`Change the status of ${legalCase.title}`"
		:actions="[{ label: saveLabel, variant: 'solid', onClick: ({ close }) => save(close) }]"
	>
		<form class="flex flex-col gap-4" @submit.prevent>
			<FormControl
				v-model="form.status"
				type="select"
				label="New status"
				:options="
					nextCaseStatuses(legalCase.status).map((value) => ({ label: value, value }))
				"
			/>
			<template v-if="closing">
				<FormControl
					v-model="form.closed_on"
					type="date"
					:format="pickerFormat()"
					label="Closed on"
					description="The date of the order, settlement or withdrawal."
					:error="missing && !form.closed_on ? 'Pick a date' : ''"
				/>
				<FormControl
					v-model="form.outcome"
					type="textarea"
					label="Outcome"
					placeholder="What was decided, and anything that follows from it"
					:rows="3"
				/>
				<div v-if="scheduled.length" class="flex flex-col gap-1">
					<p class="text-base text-ink-amber-4">{{ cancelLine(scheduled.length) }}</p>
					<ul class="flex flex-col gap-0.5 pl-1 text-sm text-ink-gray-6">
						<li v-for="legalDate in scheduled" :key="legalDate.name">
							{{ legalDate.kind }}, {{ formatDate(legalDate.date) }}
						</li>
					</ul>
				</div>
			</template>
			<p v-if="error" role="alert" class="text-base text-ink-red-4">{{ error }}</p>
		</form>
	</Dialog>
</template>

<script setup>
// A case moves on: stayed, reserved for order, closed with its outcome, or opened again.
import { computed, reactive, ref, watch } from "vue";
import { Dialog, FormControl, toast } from "frappe-ui";
import { runMethod } from "@/api";
import { noteText } from "@/lib/editing";
import { formatDate, pickerFormat } from "@/lib/format";
import {
	CLOSED_CASE_STATUSES,
	OPEN_CASE_STATUSES,
	cancelLine,
	nextCaseStatuses,
} from "@/lib/legal";
import { isoDate } from "@/lib/obligations";
import { commentHtml } from "@/lib/records";

const props = defineProps({ legalCase: { type: Object, required: true } });
const emit = defineEmits(["changed"]);
const open = defineModel("open", { type: Boolean, default: false });

const form = reactive({ status: "", closed_on: "", outcome: "" });
const scheduled = ref([]);
const missing = ref(false);
const error = ref("");

const closing = computed(() => CLOSED_CASE_STATUSES.includes(form.status));
const saveLabel = computed(() =>
	closing.value
		? "Close the case"
		: OPEN_CASE_STATUSES.includes(props.legalCase.status)
		? "Save status"
		: "Open it again"
);

watch(open, async (now) => {
	if (!now) return;
	const isOpen = OPEN_CASE_STATUSES.includes(props.legalCase.status);
	Object.assign(form, {
		status: isOpen ? CLOSED_CASE_STATUSES[0] : "Open",
		closed_on: isoDate(new Date()),
		outcome: noteText(props.legalCase.outcome),
	});
	missing.value = false;
	error.value = "";
	scheduled.value = [];
	if (!isOpen) return;
	try {
		scheduled.value = await scheduledDates("Legal Case", props.legalCase.name);
	} catch {
		// The list is only shown; the server cancels the dates whether or not it is.
		scheduled.value = [];
	}
});

async function save(close) {
	missing.value = true;
	error.value = "";
	if (closing.value && !form.closed_on) return;
	const outcome = form.outcome.trim();
	try {
		await runMethod("Legal Case", props.legalCase.name, "change_status", {
			status: form.status,
			...(closing.value
				? { closed_on: form.closed_on, outcome: outcome ? commentHtml(outcome) : null }
				: {}),
		});
		close();
		toast.success(closing.value ? "Case closed" : `Now ${form.status}`);
		emit("changed");
	} catch (err) {
		error.value = err.isNetwork
			? "Changing the status needs a connection to the server. Try again when you are back online."
			: err.message;
	}
}
</script>
