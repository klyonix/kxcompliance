<template>
	<Dialog
		v-model:open="open"
		title="Ask the client for a document"
		:actions="[
			{
				label: 'Send request',
				variant: 'solid',
				onClick: ({ close }) => send(close),
			},
		]"
	>
		<form class="flex flex-col gap-4" @submit.prevent>
			<p class="text-base text-ink-gray-6">{{ message }}</p>
			<FormControl
				v-if="!task && companies.length > 1"
				v-model="form.company"
				type="select"
				label="Company"
				:options="companies.map((value) => ({ label: value, value }))"
			/>
			<FormControl
				v-model="form.title"
				label="Document"
				placeholder="October sales register"
				:error="missing && !form.title.trim() ? 'Say what you need' : ''"
			/>
			<FormControl
				v-model="form.details"
				type="textarea"
				label="Details for the client"
				placeholder="Period, format, anything that helps them send the right thing"
				:rows="3"
			/>
			<FormControl
				v-model="form.due_date"
				type="date"
				:format="pickerFormat()"
				label="Needed by"
				:error="missing && !form.due_date ? 'Pick a date' : ''"
			/>
			<p v-if="error" role="alert" class="text-base text-ink-red-4">{{ error }}</p>
		</form>
	</Dialog>
</template>

<script setup>
// The firm asks a client for a document, from a filing or from the client's page.
import { computed, reactive, ref, watch } from "vue";
import { Dialog, FormControl } from "frappe-ui";
import { createDoc } from "@/api";
import { pickerFormat } from "@/lib/format";
import { suggestedDueDate } from "@/lib/requests";

const props = defineProps({
	// The client's companies to choose from, when not asked from a filing.
	companies: { type: Array, default: () => [] },
	task: { type: String, default: "" },
	taskLabel: { type: String, default: "" },
	filingDue: { type: String, default: "" },
});
const emit = defineEmits(["created"]);
const open = defineModel("open", { type: Boolean, default: false });

const form = reactive({ company: "", title: "", details: "", due_date: "" });
const missing = ref(false);
const error = ref("");

const message = computed(() =>
	props.task
		? `For ${props.taskLabel}. The client's logins are emailed, and reminded until it arrives.`
		: "The client's logins are emailed, and reminded until it arrives."
);

watch(open, (now) => {
	if (!now) return;
	Object.assign(form, {
		company: props.companies[0] || "",
		title: "",
		details: "",
		due_date: suggestedDueDate(props.filingDue),
	});
	missing.value = false;
	error.value = "";
});

async function send(close) {
	missing.value = true;
	error.value = "";
	if (!form.title.trim() || !form.due_date) return;
	try {
		const request = await createDoc("Document Request", {
			title: form.title.trim(),
			details: form.details.trim(),
			due_date: form.due_date,
			...(props.task ? { compliance_task: props.task } : { company: form.company }),
		});
		close();
		emit("created", request);
	} catch (err) {
		error.value = err.isNetwork
			? "The request did not reach the server. Try again when you are back online."
			: err.message;
	}
}
</script>
