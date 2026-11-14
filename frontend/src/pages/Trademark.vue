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
		:facts="facts"
		:notes="notes"
		:may-act="mayAct"
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
import { ENDED_MARK_STATUSES, markRow, plainText } from "@/lib/legal";
import { formatDate } from "@/lib/format";
import { notLoaded } from "@/offline/reachability";

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

const due = computed(() => {
	const current = mark.value;
	if (!current) return { text: "", late: false };
	if (current.status === "Registered" && current.valid_until) {
		return { text: `Registered until ${formatDate(current.valid_until)}`, late: false };
	}
	if (!current.next_date) return { text: row.value.due.text, late: false };
	return { text: `Next ${formatDate(current.next_date)} · ${row.value.due.text.toLowerCase()}` };
});

const facts = computed(() => {
	const current = mark.value;
	if (!current) return [];
	return [
		["Type", current.mark_type],
		["Brand", current.brand],
		["Applicant", current.applicant],
		["Filed on", formatDate(current.filing_date)],
		[
			"Use",
			current.user_claim === "Used since"
				? `Used since ${formatDate(current.used_since)}`
				: current.user_claim,
		],
		["Agent", current.agent],
		["Examination report", formatDate(current.examination_report_on)],
		[
			"Journal",
			[current.journal_number, formatDate(current.journal_date)].filter(Boolean).join(", "),
		],
		[
			"Opposition",
			[current.opposition_number, formatDate(current.opposition_notice_on)]
				.filter(Boolean)
				.join(", "),
		],
		[
			"Registration",
			[current.registration_number, formatDate(current.registration_date)]
				.filter(Boolean)
				.join(", "),
		],
		["Valid until", current.status === "Registered" && formatDate(current.valid_until)],
		["Responsible", current.responsible],
		["Reviewer", current.reviewer],
	];
});

const notes = computed(() => [["Notes", plainText(mark.value?.notes)]]);

async function load() {
	error.value = "";
	try {
		mark.value = await getDoc("Trademark", props.name);
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this trademark", "opened") : err.message;
	}
}

watch(() => props.name, load);
onMounted(load);
</script>
