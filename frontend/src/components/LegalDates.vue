<template>
	<section class="flex flex-col gap-3" aria-labelledby="dates-heading">
		<div class="flex items-center justify-between gap-3">
			<h2 id="dates-heading" class="text-base font-semibold text-ink-gray-8">Dates</h2>
			<Button
				v-if="mayAct"
				size="sm"
				icon-left="lucide-calendar-plus"
				label="Add a date"
				@click="addDate"
			/>
		</div>
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
		<OutcomeDialog
			v-if="outcomeFor"
			v-model:open="outcomeOpen"
			:legal-date="outcomeFor"
			:send="send"
			@saved="toast.success('Outcome recorded')"
		/>
		<LegalDateDialog
			v-model:open="dateDialogOpen"
			:doctype="doctype"
			:name="name"
			:legal-date="movingDate"
			:send="send"
			@saved="dateSaved"
		/>
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
import LegalDateDialog from "@/components/LegalDateDialog.vue";
import OutcomeDialog from "@/components/OutcomeDialog.vue";
import { dateStatus, dateTheme } from "@/lib/legal";
import { SAVED_ON_DEVICE, isWaiting, refresh as refreshOutbox } from "@/offline/outbox";
import { submit } from "@/offline/queue";
import { notLoaded } from "@/offline/reachability";
import { formatDate } from "@/lib/format";

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
		actions.push(
			{ label: "Record outcome", variant: "solid", onClick: () => recordOutcome(legalDate) },
			{ label: "Move", onClick: () => moveDate(legalDate) },
			{ label: "Cancel", onClick: () => cancelDate(legalDate) }
		);
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

// What happened at a date, in its own dialog.
const outcomeFor = ref(null);
const outcomeOpen = ref(false);

function recordOutcome(legalDate) {
	outcomeFor.value = legalDate;
	outcomeOpen.value = true;
}

// Adding a date, or moving a scheduled one, in its own dialog.
const dateDialogOpen = ref(false);
const movingDate = ref(null);

function addDate() {
	movingDate.value = null;
	dateDialogOpen.value = true;
}

function moveDate(legalDate) {
	movingDate.value = legalDate;
	dateDialogOpen.value = true;
}

// A move went through `send`, which reads the dates again; a new date is read here.
async function dateSaved(message) {
	if (!movingDate.value) {
		await load();
		emit("changed");
	}
	toast.success(message);
}

// No longer happening: the notice was withdrawn, the date was a mistake.
function cancelDate(legalDate) {
	dialog.prompt({
		title: `Cancel ${legalDate.kind.toLowerCase()}, ${when(legalDate)}?`,
		message: "No reminders go out for it. To record what happened at it, use Record outcome.",
		confirmLabel: "Cancel the date",
		cancelLabel: "Keep it",
		theme: "red",
		fields: [
			{
				name: "proceedings",
				label: "Why",
				placeholder: "Notice withdrawn by the department",
			},
		],
		onConfirm: async ({ values }) => {
			await send(legalDate, {
				status: "Cancelled",
				...(values.proceedings?.trim() ? { proceedings: values.proceedings.trim() } : {}),
			});
			toast.success("Date cancelled");
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
