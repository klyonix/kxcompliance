<template>
	<LegalRecord
		doctype="Trademark"
		:name="name"
		:loaded="Boolean(mark)"
		:error="error"
		:title="mark?.mark"
		fallback-title="Trademark"
		:status="mark?.status"
		:theme="row.theme"
		:due="due"
		:subtitle="row.detail"
		:doc="mark"
		:details="MARK_DETAILS"
		:key-facts="keyFacts"
		:may-act="mayAct"
		:may-edit="mayEdit"
		@changed="load"
	>
		<section v-if="mark?.logo || mark?.classes?.length" class="flex items-start gap-4">
			<img
				v-if="mark.logo"
				:src="mark.logo"
				:alt="`${mark.mark} logo`"
				class="size-16 shrink-0 rounded-lg bg-surface-gray-1 object-contain p-1"
			/>
			<ul class="flex min-w-0 flex-1 flex-col gap-2">
				<li v-for="entry in mark.classes" :key="entry.name" class="flex gap-3">
					<span
						class="flex h-6 min-w-8 shrink-0 items-center justify-center rounded bg-surface-gray-2 px-1.5 text-sm font-medium text-ink-gray-7"
						>{{ entry.class_number }}</span
					>
					<span class="text-base text-ink-gray-7">{{
						entry.goods_or_services || "Class " + entry.class_number
					}}</span>
				</li>
			</ul>
		</section>
	</LegalRecord>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { getDoc } from "@/api";
import { boot } from "@/boot";
import LegalRecord from "@/components/LegalRecord.vue";
import { canAct } from "@/lib/items";
import { ENDED_MARK_STATUSES, markRow } from "@/lib/legal";
import { formatDate } from "@/lib/format";
import { notLoaded } from "@/offline/reachability";
import { learnNames, nameOf } from "@/composables/usePeople";

const props = defineProps({ name: { type: String, required: true } });

const mark = ref(null);
const error = ref("");

const row = computed(() => (mark.value ? markRow(mark.value) : { detail: "" }));
const mayAct = computed(
	() =>
		Boolean(mark.value) &&
		!ENDED_MARK_STATUSES.includes(mark.value.status) &&
		canAct(mark.value, boot)
);
const mayEdit = computed(() => canAct(mark.value, boot));

const due = computed(() => {
	const current = mark.value;
	if (!current) return { text: "", late: false };
	if (current.status === "Registered" && current.valid_until) {
		return { text: `Registered until ${formatDate(current.valid_until)}`, late: false };
	}
	if (!current.next_date) return { text: row.value.due.text, late: false };
	return { text: `Next ${formatDate(current.next_date)} · ${row.value.due.text.toLowerCase()}` };
});

// The band across the top: the next date, the application, who handles it, whose mark it is.
const keyFacts = computed(() => {
	const current = mark.value;
	if (!current) return [];
	return [
		{
			label: "Next date",
			icon: "lucide-calendar-clock",
			value: current.next_date ? formatDate(current.next_date) : "Not set",
			tone: row.value.due.late ? "red" : "plain",
		},
		{ label: "Application", icon: "lucide-hash", value: current.application_number },
		{ label: "Responsible", icon: "lucide-user-round", value: nameOf(current.responsible) },
		{ label: "Applicant", icon: "lucide-building-2", value: current.applicant },
	];
});

// What the trademark page shows under Details, each changed where it is shown by those who may.
const MARK_DETAILS = [
	{ field: "mark", label: "Mark" },
	{ field: "mark_type", label: "Type" },
	{ field: "brand", label: "Brand", show: (current) => current.brand },
	{ field: "applicant", label: "Applicant", show: (current) => current.applicant },
	{ field: "application_number", label: "Application number" },
	{ field: "filing_date", label: "Filed on" },
	{ field: "user_claim", label: "Use" },
	{
		field: "used_since",
		label: "Used since",
		when: (current) => current.user_claim === "Used since",
	},
	{ field: "agent", label: "Agent", show: (current) => current.agent },
	{ field: "examination_report_on", label: "Examination report" },
	{ field: "journal_number", label: "Journal number" },
	{ field: "journal_date", label: "Journal date" },
	{ field: "opposition_number", label: "Opposition number" },
	{ field: "opposition_notice_on", label: "Opposition notice" },
	{ field: "registration_number", label: "Registration number" },
	{ field: "registration_date", label: "Registered on" },
	{
		field: "valid_until",
		label: "Valid until",
		show: (current) =>
			current.status === "Registered" ? formatDate(current.valid_until) : "",
	},
	{ field: "responsible", label: "Responsible" },
	{ field: "reviewer", label: "Reviewer" },
	{ field: "notes", label: "Notes" },
];

async function load() {
	error.value = "";
	try {
		mark.value = await getDoc("Trademark", props.name);
		learnNames([mark.value.responsible, mark.value.reviewer]);
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this trademark", "opened") : err.message;
	}
}

watch(() => props.name, load);
onMounted(load);
</script>
