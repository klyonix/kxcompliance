<template>
	<LegalRecord
		doctype="Legal Case"
		:name="name"
		:loaded="Boolean(legalCase)"
		:error="error"
		:title="legalCase?.title"
		fallback-title="Case"
		:status="legalCase?.status"
		:theme="row.theme"
		:due="due"
		:subtitle="row.detail"
		:facts="facts"
		:notes="notes"
		:may-act="mayAct"
		@changed="load"
	>
		<section
			v-if="exposure"
			class="grid grid-cols-3 gap-3 rounded-lg bg-surface-gray-1 px-4 py-3"
			aria-label="Amounts"
		>
			<div v-for="figure in exposure" :key="figure.label" class="flex flex-col gap-0.5">
				<span class="text-sm text-ink-gray-5">{{ figure.label }}</span>
				<span class="text-base font-medium text-ink-gray-8">{{ figure.value }}</span>
			</div>
		</section>
	</LegalRecord>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { getDoc } from "@/api";
import { boot } from "@/boot";
import LegalRecord from "@/components/LegalRecord.vue";
import { canAct } from "@/lib/items";
import { OPEN_CASE_STATUSES, caseRow, plainText } from "@/lib/legal";
import { formatDate } from "@/lib/format";
import { notLoaded } from "@/offline/reachability";
import { learnNames, nameOf } from "@/composables/usePeople";

const props = defineProps({ name: { type: String, required: true } });

const legalCase = ref(null);
const error = ref("");

const row = computed(() => (legalCase.value ? caseRow(legalCase.value) : { detail: "" }));
const open = computed(() => OPEN_CASE_STATUSES.includes(legalCase.value?.status));
const mayAct = computed(() => open.value && canAct(legalCase.value, boot));

const formatAmount = (value, currency) =>
	Number(value || 0).toLocaleString(undefined, {
		style: currency ? "currency" : "decimal",
		currency: currency || undefined,
		maximumFractionDigits: 0,
	});

const due = computed(() => {
	const current = legalCase.value;
	if (!current) return { text: "", late: false };
	if (!open.value) {
		return { text: current.closed_on ? `Closed ${formatDate(current.closed_on)}` : "" };
	}
	if (!current.next_date) return { text: "No date set", late: false };
	return { text: `Next ${formatDate(current.next_date)} · ${row.value.due.text.toLowerCase()}` };
});

// Only Compliance Managers and Auditors receive these; for anyone else the server leaves them out.
const exposure = computed(() => {
	const current = legalCase.value;
	if (!current || !("amount_involved" in current) || !current.amount_involved) return null;
	return [
		{ label: "Involved", value: formatAmount(current.amount_involved, current.currency) },
		{ label: "Provided", value: formatAmount(current.provision, current.currency) },
		{ label: "Risk", value: current.risk || "Not rated" },
	];
});

const facts = computed(() => {
	const current = legalCase.value;
	if (!current) return [];
	return [
		["Case number", current.case_number],
		["CNR number", current.cnr_number],
		["Notice reference", current.notice_reference],
		["Forum", [current.forum_name || current.forum, current.bench].filter(Boolean).join(", ")],
		["State", current.state],
		["Filed or received on", formatDate(current.filing_date)],
		["Company", current.company],
		["Our role", current.our_role],
		["Opposing party", current.opposing_party],
		["Advocate", [current.advocate, current.advocate_contact].filter(Boolean).join(" · ")],
		["Appeal of", current.appeal_of],
		["Responsible", nameOf(current.responsible)],
		["Reviewer", nameOf(current.reviewer)],
	];
});

const notes = computed(() => [
	["Summary", plainText(legalCase.value?.summary)],
	["Outcome", plainText(legalCase.value?.outcome)],
]);

async function load() {
	error.value = "";
	try {
		legalCase.value = await getDoc("Legal Case", props.name);
		learnNames([legalCase.value.responsible, legalCase.value.reviewer]);
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this case", "opened") : err.message;
	}
}

watch(() => props.name, load);
onMounted(load);
</script>
