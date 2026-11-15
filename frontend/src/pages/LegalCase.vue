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
		:doc="legalCase"
		:details="CASE_DETAILS"
		:key-facts="keyFacts"
		:may-act="mayAct"
		:may-edit="mayEdit"
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
import { OPEN_CASE_STATUSES, caseRow } from "@/lib/legal";
import { formatDate } from "@/lib/format";
import { notLoaded } from "@/offline/reachability";
import { learnNames, nameOf } from "@/composables/usePeople";

const props = defineProps({ name: { type: String, required: true } });

const legalCase = ref(null);
const error = ref("");

const row = computed(() => (legalCase.value ? caseRow(legalCase.value) : { detail: "" }));
const open = computed(() => OPEN_CASE_STATUSES.includes(legalCase.value?.status));
const mayAct = computed(() => open.value && canAct(legalCase.value, boot));
const mayEdit = computed(() => canAct(legalCase.value, boot));

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

// The band across the top: the next date, where the case is heard, who handles it, whose it is.
const keyFacts = computed(() => {
	const current = legalCase.value;
	return [
		{
			label: "Next date",
			icon: "lucide-calendar-clock",
			value: current.next_date ? formatDate(current.next_date) : "Not set",
			tone: row.value.due.late ? "red" : "plain",
		},
		{ label: "Forum", icon: "lucide-landmark", value: current.forum_name || current.forum },
		{ label: "Responsible", icon: "lucide-user-round", value: nameOf(current.responsible) },
		{ label: "Company", icon: "lucide-building-2", value: current.company },
	];
});

// What the case page shows under Details, each changed where it is shown by those who may.
const CASE_DETAILS = [
	{ field: "title", label: "Title" },
	{ field: "case_type", label: "Type" },
	{ field: "case_number", label: "Case number" },
	{ field: "cnr_number", label: "CNR number" },
	{ field: "notice_reference", label: "Notice reference" },
	{ field: "forum", label: "Forum" },
	{ field: "forum_name", label: "Forum name" },
	{ field: "bench", label: "Bench" },
	{ field: "state", label: "State" },
	{ field: "filing_date", label: "Filed or received on" },
	{ field: "company", label: "Company", show: (current) => current.company },
	{ field: "our_role", label: "Our role" },
	{ field: "opposing_party", label: "Opposing party" },
	{ field: "advocate", label: "Advocate", show: (current) => current.advocate },
	{ field: "advocate_contact", label: "Advocate's contact" },
	{ field: "appeal_of", label: "Appeal of", show: (current) => current.appeal_of },
	{ field: "responsible", label: "Responsible" },
	{ field: "reviewer", label: "Reviewer" },
	{ field: "summary", label: "Summary" },
	{ field: "outcome", label: "Outcome" },
];

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
