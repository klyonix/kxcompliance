<template>
	<Dialog
		v-model:open="open"
		:title="t('Statement of account')"
		:actions="[{ label: t('Download PDF'), variant: 'solid', onClick: download }]"
	>
		<form class="flex flex-col gap-4" @submit.prevent>
			<p class="text-base text-ink-gray-6">
				{{
					own
						? t(
								"Every bill, payment and credit between these dates, with the balance after each."
						  )
						: "Every bill, payment, TDS, credit note and write-off between these dates, with the balance after each. The client can download its own from its login."
				}}
			</p>
			<div class="grid grid-cols-2 gap-3">
				<FormControl v-model="from" type="date" :label="t('From')" />
				<FormControl v-model="to" type="date" :label="t('To')" />
			</div>
			<p v-if="error" role="alert" class="text-base text-ink-red-4">{{ error }}</p>
		</form>
	</Dialog>
</template>

<script setup>
// Choosing the dates of a client's statement of account, then opening it as a PDF.
import { ref, watch } from "vue";
import { Dialog, FormControl } from "frappe-ui";
import { statementLink, statementProblem } from "@/lib/billing";
import { t } from "@/lib/i18n";

const props = defineProps({
	client: { type: String, required: true },
	// The financial year, which the dates start as.
	year: { type: Object, required: true },
	// The client's own login, rather than the firm.
	own: { type: Boolean, default: false },
});
const open = defineModel("open", { type: Boolean, default: false });

const from = ref("");
const to = ref("");
const error = ref("");

watch(open, (now) => {
	if (!now) return;
	from.value = props.year.from_date;
	to.value = props.year.to_date;
	error.value = "";
});

function download({ close }) {
	const problem = statementProblem({ from: from.value, to: to.value });
	error.value = problem ? t(problem) : "";
	if (error.value) return;
	window.open(statementLink(props.client, from.value, to.value), "_blank");
	close();
}
</script>
