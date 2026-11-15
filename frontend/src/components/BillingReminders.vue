<template>
	<section class="flex flex-col gap-4" aria-labelledby="reminders-heading">
		<div class="flex flex-col gap-0.5">
			<h2 id="reminders-heading" class="text-base font-semibold text-ink-gray-8">
				Overdue reminders
			</h2>
			<p class="text-sm text-ink-gray-5">
				A client whose bill is past its due date is emailed the bill again, once at each
				step, until it is paid. Each reminder is kept in the reminder log.
			</p>
		</div>
		<FormControl
			v-model="form.overdue_reminders"
			type="checkbox"
			label="Remind clients of overdue bills"
		/>
		<FormControl
			v-model="form.reminder_steps"
			label="Days late to remind on"
			placeholder="3, 15, 30"
			:disabled="!form.overdue_reminders"
			description="Days after the due date, separated by commas."
		/>
		<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
			<p v-if="saveError" role="alert" class="text-sm text-ink-red-4 sm:mr-auto">
				{{ saveError }}
			</p>
			<Button variant="solid" label="Save reminders" :loading="saving" @click="save" />
		</div>
	</section>
</template>

<script setup>
// Billing settings, the Reminders tab: whether clients are reminded of overdue bills, and when.
import { reactive, ref, watch } from "vue";
import { Button, FormControl, toast } from "frappe-ui";
import { call } from "@/api";

const props = defineProps({ setup: { type: Object, required: true } });
const emit = defineEmits(["saved"]);

const form = reactive({ overdue_reminders: false, reminder_steps: "" });
const saveError = ref("");
const saving = ref(false);

watch(
	() => props.setup,
	(state) => {
		form.overdue_reminders = Boolean(Number(state.overdue_reminders));
		form.reminder_steps = state.reminder_steps || "3, 15, 30";
	},
	{ immediate: true }
);

async function save() {
	saveError.value = "";
	saving.value = true;
	try {
		const state = await call(
			"kxcompliance.api.set_up_billing",
			{
				details: {
					overdue_reminders: form.overdue_reminders ? 1 : 0,
					reminder_steps: form.reminder_steps.trim(),
				},
			},
			{ httpMethod: "POST" }
		);
		toast.success("Reminders saved");
		emit("saved", state);
	} catch (err) {
		saveError.value = err.message;
	} finally {
		saving.value = false;
	}
}
</script>
