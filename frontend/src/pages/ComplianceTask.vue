<template>
	<AppPageHeader :title="task?.obligation_template || 'Filing'">
		<template #actions>
			<Dropdown v-if="task" :options="menu" align="end">
				<Button variant="ghost" icon="lucide-ellipsis" label="More actions" />
			</Dropdown>
		</template>
	</AppPageHeader>

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-6 sm:px-6">
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>

		<div v-else-if="!task" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton class="h-6 w-1/2 rounded" />
			<Skeleton class="h-4 w-1/3 rounded" />
			<Skeleton class="mt-4 h-48 w-full rounded-lg" />
		</div>

		<template v-else>
			<section class="flex flex-col gap-2">
				<div class="flex flex-wrap items-center gap-2">
					<Badge :label="task.status" :theme="row.theme" size="md" />
					<span
						class="text-base"
						:class="row.due.late ? 'font-medium text-ink-red-4' : 'text-ink-gray-6'"
					>
						{{ dueLine }}
					</span>
				</div>
				<p class="text-base text-ink-gray-6">{{ row.detail }}</p>
				<p
					v-if="waiting"
					class="flex items-center gap-2 rounded-lg bg-surface-amber-1 px-3 py-2 text-base text-ink-amber-4"
				>
					<span class="lucide-cloud-off size-4 shrink-0" aria-hidden="true" />
					Your change is saved on this device and will be sent as soon as the server can
					be reached.
				</p>
				<p
					v-else-if="reviewNote"
					class="rounded-lg bg-surface-gray-2 px-3 py-2 text-base text-ink-gray-7"
				>
					{{ reviewNote }}
				</p>
			</section>

			<section class="flex flex-col gap-4" aria-labelledby="filing-heading">
				<h2 id="filing-heading" class="text-base font-semibold text-ink-gray-8">Filing</h2>

				<template v-if="editable">
					<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
						<FormControl
							v-model="form.filed_on"
							type="date"
							label="Filed on"
							placeholder="Pick a date"
							:error="fieldError('Filed on')"
						/>
						<FormControl
							v-model="form.acknowledgement_number"
							label="Acknowledgement number"
							placeholder="ARN, challan or SRN"
							:error="fieldError('Acknowledgement number')"
						/>
					</div>

					<div class="flex flex-col gap-1.5">
						<span class="text-xs text-ink-gray-5">
							Proof<template v-if="rules?.requires_proof"> (needed)</template>
						</span>
						<div
							class="flex items-center gap-3 rounded-lg bg-surface-gray-1 px-3 py-3"
							:class="fieldError('Proof') ? 'ring-1 ring-outline-red-3' : ''"
						>
							<span
								class="flex size-9 shrink-0 items-center justify-center rounded-lg bg-surface-base text-ink-gray-6"
							>
								<span
									:class="hasProof ? 'lucide-file-check' : 'lucide-file-plus'"
									class="size-5"
									aria-hidden="true"
								/>
							</span>
							<div class="flex min-w-0 flex-1 flex-col">
								<span class="truncate text-base text-ink-gray-8">{{
									proofLabel
								}}</span>
								<span v-if="proofFile" class="text-sm text-ink-gray-5"
									>Sent with your next save</span
								>
								<span v-else-if="!task.proof" class="text-sm text-ink-gray-5"
									>The acknowledgement or challan, as a photo or a PDF</span
								>
							</div>
							<Button
								v-if="task.proof && !proofFile"
								label="View"
								:href="task.proof"
								target="_blank"
							/>
							<Button :label="hasProof ? 'Replace' : 'Attach'" @click="chooseFile" />
							<input
								ref="fileInput"
								type="file"
								accept="image/*,application/pdf"
								class="hidden"
								@change="pickProof"
							/>
						</div>
						<p v-if="fieldError('Proof')" class="text-sm text-ink-red-4">
							{{ fieldError("Proof") }}
						</p>
					</div>

					<div v-if="showAmounts" class="grid grid-cols-1 gap-4 sm:grid-cols-3">
						<FormControl
							v-model="form.amount_paid"
							type="number"
							label="Amount paid"
							placeholder="0.00"
						/>
						<FormControl
							v-model="form.interest"
							type="number"
							label="Interest"
							placeholder="0.00"
						/>
						<FormControl
							v-model="form.late_fee"
							type="number"
							label="Late fee"
							placeholder="0.00"
						/>
					</div>

					<FormControl
						v-model="form.remarks"
						type="textarea"
						label="Remarks"
						placeholder="Anything the reviewer or an auditor should know"
						:rows="3"
					/>
				</template>

				<dl v-else class="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
					<div
						v-for="fact in filingFacts"
						:key="fact.label"
						class="flex flex-col gap-0.5"
					>
						<dt class="text-sm text-ink-gray-5">{{ fact.label }}</dt>
						<dd class="text-base text-ink-gray-8">
							<a
								v-if="fact.href"
								:href="fact.href"
								target="_blank"
								class="underline decoration-outline-gray-3 underline-offset-2"
								>{{ fact.value }}</a
							>
							<template v-else>{{ fact.value }}</template>
						</dd>
					</div>
					<p v-if="!filingFacts.length" class="text-base text-ink-gray-5">
						Nothing recorded yet.
					</p>
				</dl>
			</section>

			<section class="flex flex-col gap-3" aria-labelledby="details-heading">
				<h2 id="details-heading" class="text-base font-semibold text-ink-gray-8">
					Details
				</h2>
				<dl class="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
					<div v-for="fact in facts" :key="fact.label" class="flex flex-col gap-0.5">
						<dt class="text-sm text-ink-gray-5">{{ fact.label }}</dt>
						<dd class="text-base text-ink-gray-8">{{ fact.value }}</dd>
					</div>
				</dl>
			</section>
		</template>
	</div>

	<!-- The actions stay in reach at the foot of the screen, on a phone above the tab bar. -->
	<div
		v-if="editable"
		class="sticky bottom-0 z-10 mt-auto border-t border-outline-gray-1 bg-surface-base"
	>
		<div
			class="mx-auto flex w-full max-w-3xl flex-col-reverse gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-end sm:px-6"
		>
			<p v-if="footerError" role="alert" class="text-sm text-ink-red-4 sm:mr-auto">
				{{ footerError }}
			</p>
			<Button
				v-if="actions.sendBack"
				label="Send back"
				:size="buttonSize"
				:disabled="Boolean(busy) || waiting"
				@click="sendBack"
			/>
			<Button
				label="Save"
				:size="buttonSize"
				:loading="busy === 'save'"
				:disabled="Boolean(busy) || waiting || !dirty"
				@click="save()"
			/>
			<Button
				v-if="primary"
				variant="solid"
				:label="primary.label"
				:size="buttonSize"
				:loading="busy === primary.status"
				:disabled="Boolean(busy) || waiting"
				@click="save(primary.status)"
			/>
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { Badge, Button, Dropdown, FormControl, Skeleton, dialog, toast } from "frappe-ui";
import { getDoc } from "@/api";
import { boot } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import {
	FILING_FIELDS,
	changedValues,
	formValues,
	missingDetails,
	taskActions,
	taskRow,
} from "@/lib/filings";
import { deskRoute } from "@/navigation";
import { SAVED_ON_DEVICE, refresh as refreshOutbox } from "@/offline/outbox";
import { submit } from "@/offline/queue";
import { formatDate } from "@/lib/format";
import { notLoaded } from "@/offline/reachability";

const props = defineProps({ name: { type: String, required: true } });

const task = ref(null);
const rules = ref(null);
const error = ref("");
const formError = ref("");
// Set once someone tries to send the filing on; the gaps then show and clear as they are filled.
const checking = ref(false);
const busy = ref("");
const waiting = ref(false);
const proofFile = ref(null);
const fileInput = ref(null);
const form = reactive(Object.fromEntries(FILING_FIELDS.map((field) => [field, ""])));

const isMobile = useIsMobile();
const buttonSize = computed(() => (isMobile.value ? "md" : "sm"));

const row = computed(() => taskRow(task.value));
const actions = computed(() => taskActions(task.value, rules.value, boot));
const editable = computed(() => actions.value.edit);
const hasProof = computed(() => Boolean(proofFile.value || task.value?.proof));
const dirty = computed(
	() => Boolean(proofFile.value) || Object.keys(changedValues(form, task.value || {})).length > 0
);
const showAmounts = computed(
	() =>
		Boolean(rules.value?.requires_payment) ||
		["amount_paid", "interest", "late_fee"].some((field) => Number(task.value?.[field]))
);

// One main step: send a reviewed filing on for review, or mark it filed.
const primary = computed(() => {
	if (actions.value.sendForReview && !actions.value.markFiled) {
		return { label: "Send for review", status: "Ready for Review" };
	}
	if (actions.value.markFiled) return { label: "Mark filed", status: "Filed" };
	return null;
});

const formatAmount = (value) =>
	Number(value)
		? Number(value).toLocaleString(undefined, {
				minimumFractionDigits: 2,
				maximumFractionDigits: 2,
		  })
		: "";

const dueLine = computed(() => {
	const due = `Due ${formatDate(task.value.effective_due_date)}`;
	return row.value.due.text && !row.value.due.text.startsWith("Filed")
		? `${due} · ${row.value.due.text.toLowerCase()}`
		: due;
});

const reviewNote = computed(() => {
	const current = task.value;
	if (current.status !== "Ready for Review") return "";
	if (actions.value.markFiled) {
		return "Check the details and proof, then mark it filed or send it back with a remark.";
	}
	return `Waiting for ${
		current.reviewer || "a Compliance Manager"
	} to check it and mark it filed.`;
});

const proofLabel = computed(() => {
	if (proofFile.value) return proofFile.value.name;
	if (!task.value.proof) return "No proof attached";
	return decodeURIComponent(task.value.proof.split("/").pop());
});

const filingFacts = computed(() =>
	[
		["Filed on", formatDate(task.value.filed_on)],
		["Acknowledgement number", task.value.acknowledgement_number],
		[
			"Proof",
			task.value.proof && decodeURIComponent(task.value.proof.split("/").pop()),
			task.value.proof,
		],
		["Amount paid", formatAmount(task.value.amount_paid)],
		["Interest", formatAmount(task.value.interest)],
		["Late fee", formatAmount(task.value.late_fee)],
		["Reviewed by", task.value.reviewed_by],
		["Remarks", task.value.remarks],
	]
		.filter(([, value]) => value)
		.map(([label, value, href]) => ({ label, value, href }))
);

const facts = computed(() =>
	[
		["Period", task.value.period_label],
		["Company", task.value.company],
		["Law", task.value.law],
		["Registration", task.value.registration_number],
		["State", task.value.state],
		[
			"Due date",
			task.value.extended_due_date
				? `${formatDate(task.value.extended_due_date)} (extended from ${formatDate(
						task.value.due_date
				  )})`
				: formatDate(task.value.due_date),
		],
		["Responsible", task.value.responsible],
		["Reviewer", task.value.reviewer],
	]
		.filter(([, value]) => value)
		.map(([label, value]) => ({ label, value }))
);

const menu = computed(() => [
	{
		label: "Open in the Desk",
		icon: "lucide-app-window",
		onClick: () => (window.location.href = deskRoute("Compliance Task", props.name)),
	},
	...(editable.value
		? [{ label: "Does not apply", icon: "lucide-circle-slash", onClick: notApplicable }]
		: []),
]);

const missing = computed(() =>
	checking.value && task.value
		? missingDetails({ ...task.value, ...form }, rules.value, {
				proofWaiting: Boolean(proofFile.value),
		  })
		: []
);
const footerError = computed(() =>
	missing.value.length ? `Fill in ${missing.value.join(", ")} first.` : formError.value
);
const fieldError = (label) =>
	missing.value.includes(label) ? `Needed before ${primary.value?.label.toLowerCase()}` : "";

function fillForm() {
	Object.assign(form, formValues(task.value));
	proofFile.value = null;
	checking.value = false;
	formError.value = "";
}

async function load() {
	error.value = "";
	try {
		task.value = await getDoc("Compliance Task", props.name);
		rules.value = await getDoc(
			"Compliance Obligation Template",
			task.value.obligation_template
		);
		fillForm();
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this filing", "opened") : err.message;
	}
}

const chooseFile = () => fileInput.value?.click();

function pickProof(event) {
	const file = event.target.files?.[0];
	event.target.value = "";
	if (file) proofFile.value = file;
}

async function send(values, busyKey) {
	busy.value = busyKey;
	formError.value = "";
	try {
		const result = await submit({
			doctype: "Compliance Task",
			name: props.name,
			values,
			baseModified: task.value.modified,
			files: proofFile.value
				? [{ field: "proof", blob: proofFile.value, fileName: proofFile.value.name }]
				: [],
		});
		if (result.queued) {
			waiting.value = true;
			toast.info(SAVED_ON_DEVICE);
		} else {
			toast.success(
				{ "Ready for Review": "Sent for review", Filed: "Marked filed" }[values.status] ||
					"Saved"
			);
			await load();
		}
		return true;
	} catch (err) {
		formError.value = err.message;
		return false;
	} finally {
		busy.value = "";
		await refreshOutbox();
	}
}

function save(status) {
	const values = changedValues(form, task.value);
	if (status) {
		checking.value = true;
		if (missing.value.length) return;
		values.status = status;
	}
	return send(values, status || "save");
}

function sendBack() {
	dialog.prompt({
		title: "Send back",
		message: `${task.value.responsible} gets it back to correct. Say what needs to change.`,
		confirmLabel: "Send back",
		fields: [
			{
				name: "remarks",
				label: "What needs to change",
				type: "textarea",
				required: true,
				defaultValue: form.remarks,
			},
		],
		onConfirm: async ({ values }) => {
			await send(
				{
					...changedValues(form, task.value),
					remarks: values.remarks,
					status: "In Progress",
				},
				"back"
			);
		},
	});
}

function notApplicable() {
	dialog.prompt({
		title: "Does not apply",
		message: "The filing is closed as not applicable for this period, with your reason.",
		confirmLabel: "Close filing",
		fields: [
			{
				name: "remarks",
				label: "Why it does not apply",
				type: "textarea",
				required: true,
				defaultValue: form.remarks,
			},
		],
		onConfirm: async ({ values }) => {
			await send({ remarks: values.remarks, status: "Not Applicable" }, "na");
		},
	});
}

watch(
	() => props.name,
	() => {
		waiting.value = false;
		load();
	}
);
onMounted(load);
</script>
