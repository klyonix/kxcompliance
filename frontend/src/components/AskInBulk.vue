<template>
	<Dialog
		v-model:open="open"
		title="Ask the clients for a document"
		:actions="[
			{
				label: askLabel,
				variant: 'solid',
				disabled: !plan?.to_ask,
				onClick: ({ close }) => send(close),
			},
		]"
	>
		<form class="flex flex-col gap-4" @submit.prevent>
			<p class="text-base text-ink-gray-6">
				For {{ returnLabel }}. One request goes on each filing, needed a day before it is
				due. The client's logins are emailed, and reminded until it arrives.
			</p>
			<Skeleton v-if="!plan && !error" class="h-5 w-3/4 rounded" />
			<p v-else-if="plan" class="text-base text-ink-gray-8" aria-live="polite">
				{{ askPlanLine(plan) }}
			</p>
			<FormControl
				v-model="form.title"
				label="Document"
				placeholder="October sales register"
				:error="missing && !form.title.trim() ? 'Say what you need' : ''"
			/>
			<FormControl
				v-model="form.details"
				type="textarea"
				label="Details for the clients"
				placeholder="Format, anything that helps them send the right thing"
				:rows="3"
			/>
			<p v-if="error" role="alert" class="text-base text-ink-red-4">{{ error }}</p>
		</form>
	</Dialog>
</template>

<script setup>
// The firm asks every client with an open filing of one return and period for the same document.
import { computed, reactive, ref, watch } from "vue";
import { Dialog, FormControl, Skeleton, toast } from "frappe-ui";
import { call } from "@/api";
import { askPlanLine } from "@/lib/bulkFiling";

const props = defineProps({
	template: { type: String, required: true },
	periodEnd: { type: String, required: true },
	returnLabel: { type: String, default: "" },
	// The client filter's companies, or null for every client.
	companies: { type: Array, default: null },
});
const open = defineModel("open", { type: Boolean, default: false });

const form = reactive({ title: "", details: "" });
const plan = ref(null);
const missing = ref(false);
const error = ref("");

const params = () => ({
	obligation_template: props.template,
	period_end: props.periodEnd,
	...(props.companies ? { companies: JSON.stringify(props.companies) } : {}),
});
const askLabel = computed(() =>
	plan.value?.to_ask === 1 ? "Send 1 request" : `Send ${plan.value?.to_ask || 0} requests`
);

const friendly = (err, what) =>
	err.isNetwork ? `${what} did not reach the server. Try again when you are back online.` : err.message;

watch(open, async (now) => {
	if (!now) return;
	Object.assign(form, { title: "", details: "" });
	plan.value = null;
	missing.value = false;
	error.value = "";
	try {
		plan.value = await call("kxcompliance.api.bulk_ask_plan", params());
	} catch (err) {
		error.value = friendly(err, "The check of who to ask");
	}
});

async function send(close) {
	missing.value = true;
	error.value = "";
	if (!form.title.trim()) return;
	try {
		const { asking } = await call(
			"kxcompliance.api.ask_clients_in_bulk",
			{ ...params(), title: form.title.trim(), details: form.details.trim() },
			{ httpMethod: "POST" }
		);
		close();
		toast.success(
			`Sending ${asking === 1 ? "1 request" : `${asking} requests`}. You will be told when it is done.`
		);
	} catch (err) {
		error.value = friendly(err, "The request");
	}
}
</script>
