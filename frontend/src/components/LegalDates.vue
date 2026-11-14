<template>
	<section class="flex flex-col gap-3" aria-labelledby="dates-heading">
		<h2 id="dates-heading" class="text-base font-semibold text-ink-gray-8">Dates</h2>
		<p v-if="error" class="text-base text-ink-red-4">{{ error }}</p>
		<p v-else-if="!dates.length" class="text-base text-ink-gray-5">
			{{ loaded ? "No hearings or deadlines recorded yet." : "Loading…" }}
		</p>
		<ol v-else class="flex flex-col">
			<li
				v-for="legalDate in dates"
				:key="legalDate.name"
				class="flex flex-col gap-2 border-b border-outline-gray-1 py-3 last:border-b-0"
			>
				<div class="flex items-start gap-3">
					<div
						class="flex w-12 shrink-0 flex-col items-center rounded-lg bg-surface-gray-2 py-1"
					>
						<span class="text-xs uppercase text-ink-gray-5">{{
							month(legalDate.date)
						}}</span>
						<span class="text-lg font-semibold leading-tight text-ink-gray-8">{{
							day(legalDate.date)
						}}</span>
					</div>
					<div class="flex min-w-0 flex-1 flex-col gap-0.5">
						<div class="flex flex-wrap items-center gap-2">
							<span class="text-base font-medium text-ink-gray-8">{{
								legalDate.kind
							}}</span>
							<Badge :label="dateStatus(legalDate)" :theme="dateTheme(legalDate)" />
						</div>
						<span class="text-sm text-ink-gray-5">{{ when(legalDate) }}</span>
						<p v-if="legalDate.purpose" class="text-sm text-ink-gray-6">
							{{ legalDate.purpose }}
						</p>
						<p
							v-if="legalDate.proceedings"
							class="whitespace-pre-line text-base text-ink-gray-7"
						>
							{{ legalDate.proceedings }}
						</p>
						<p v-if="legalDate.attended_by" class="text-sm text-ink-gray-5">
							Attended by {{ legalDate.attended_by }}
						</p>
						<p
							v-if="isWaiting('Legal Date', legalDate.name)"
							class="text-sm text-ink-amber-4"
						>
							Waiting to send
						</p>
					</div>
				</div>
				<div v-if="actionsFor(legalDate).length" class="flex flex-wrap gap-2 pl-[3.75rem]">
					<Button
						v-for="action in actionsFor(legalDate)"
						:key="action.label"
						:label="action.label"
						:variant="action.variant || 'subtle'"
						:href="action.href"
						:target="action.href ? '_blank' : undefined"
						@click="action.onClick?.()"
					/>
				</div>
			</li>
		</ol>
		<input
			ref="fileInput"
			type="file"
			accept="image/*,application/pdf"
			class="hidden"
			@change="attachOrder"
		/>
	</section>
</template>

<script setup>
// The hearings and deadlines of one case or trademark, where the outcome of each is recorded.
import { computed, onMounted, ref, watch } from "vue";
import { Badge, Button, dialog, toast } from "frappe-ui";
import { getList } from "@/api";
import {
	OUTCOME_STATUSES,
	dateStatus,
	dateTheme,
	nextDateError,
	outcomeValues,
	proceedingsError,
} from "@/lib/legal";
import { SAVED_ON_DEVICE, isWaiting, refresh as refreshOutbox } from "@/offline/outbox";
import { submit } from "@/offline/queue";
import { notLoaded } from "@/offline/reachability";
import { formatDate, pickerFormat } from "@/lib/format";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, required: true },
	mayAct: { type: Boolean, default: false },
});
const emit = defineEmits(["changed"]);

const dates = ref([]);
const loaded = ref(false);
const error = ref("");
// The dates with a change kept on the device; when one is sent, the dates are read again.
const waitingDates = computed(() =>
	dates.value
		.filter((legalDate) => isWaiting("Legal Date", legalDate.name))
		.map((legalDate) => legalDate.name)
);
const fileInput = ref(null);
let orderFor = null;

const toDate = (value) => new Date(`${value}T00:00:00`);
const month = (value) => toDate(value).toLocaleDateString(undefined, { month: "short" });
const day = (value) => toDate(value).getDate();
const when = (legalDate) =>
	[formatDate(legalDate.date, { weekday: true }), legalDate.time && legalDate.time.slice(0, 5)]
		.filter(Boolean)
		.join(" at ");

function actionsFor(legalDate) {
	const actions = [];
	if (legalDate.order) {
		actions.push({ label: "View order", href: legalDate.order });
	}
	if (!props.mayAct || isWaiting("Legal Date", legalDate.name)) return actions;
	if (legalDate.status === "Scheduled") {
		actions.push({
			label: "Record outcome",
			variant: "solid",
			onClick: () => recordOutcome(legalDate),
		});
	} else if (["Done", "Adjourned"].includes(legalDate.status)) {
		actions.push({
			label: legalDate.order ? "Replace order" : "Attach order",
			onClick: () => chooseOrder(legalDate),
		});
	}
	return actions;
}

async function load() {
	error.value = "";
	try {
		dates.value = (
			await getList("Legal Date", {
				fields: [
					"name",
					"kind",
					"date",
					"time",
					"status",
					"is_overdue",
					"purpose",
					"attended_by",
					"proceedings",
					"order",
					"modified",
				],
				filters: [
					["reference_doctype", "=", props.doctype],
					["reference_name", "=", props.name],
				],
				orderBy: "date desc",
				limit: 100,
			})
		).rows;
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("these dates") : err.message;
	} finally {
		loaded.value = true;
	}
}

async function send(legalDate, values, files = []) {
	const result = await submit({
		doctype: "Legal Date",
		name: legalDate.name,
		values,
		baseModified: legalDate.modified,
		files,
	});
	if (result.queued) {
		toast.info(SAVED_ON_DEVICE);
	} else {
		await load();
		emit("changed");
	}
	await refreshOutbox();
	return result;
}

function recordOutcome(legalDate) {
	dialog.prompt({
		title: `${legalDate.kind}, ${when(legalDate)}`,
		confirmLabel: "Save outcome",
		fields: [
			{
				name: "status",
				label: "What happened",
				type: "select",
				defaultValue: "Done",
				options: OUTCOME_STATUSES.map((status) => ({ label: status, value: status })),
			},
			{ name: "attended_by", label: "Attended by", placeholder: "Advocate or staff" },
			{
				name: "proceedings",
				label: "Proceedings",
				type: "textarea",
				placeholder: "What was argued, filed or directed",
				validate: (value, values) =>
					proceedingsError(legalDate.kind, values.status, value),
			},
			{
				name: "next_date",
				label: "Next date",
				type: "date",
				format: pickerFormat(),
				description: "A new hearing or deadline is added on this date.",
				validate: (value) => nextDateError(legalDate.date, value),
			},
		],
		onConfirm: async ({ values }) => {
			await send(legalDate, outcomeValues(values));
			toast.success("Outcome recorded");
		},
	});
}

function chooseOrder(legalDate) {
	orderFor = legalDate;
	fileInput.value?.click();
}

async function attachOrder(event) {
	const file = event.target.files?.[0];
	event.target.value = "";
	if (!file || !orderFor) return;
	try {
		const result = await send(orderFor, {}, [
			{ field: "order", blob: file, fileName: file.name },
		]);
		if (!result.queued) toast.success("Order attached");
	} catch (err) {
		toast.error(err.message);
	}
}

watch(waitingDates, async (now, before) => {
	if (before.some((name) => !now.includes(name))) {
		await load();
		emit("changed");
	}
});
watch(() => props.name, load);
onMounted(load);
defineExpose({ load });
</script>
