<template>
	<AppPageHeader
		:title="task?.obligation_template || 'Filing'"
		:parent="{ label: 'Filings', route: { name: 'Filings' } }"
	>
		<template #actions>
			<Dropdown v-if="task && menu.length" :options="menu" align="end">
				<Button variant="ghost" icon="lucide-ellipsis" label="More actions" />
			</Dropdown>
		</template>
	</AppPageHeader>

	<RecordFrame
		doctype="Compliance Task"
		:name="name"
		:facts="task ? keyFacts : []"
		:modified="task?.modified || ''"
	>
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
					<Badge v-if="task.is_nil" label="NIL" theme="gray" size="md" />
					<Badge v-if="task.is_time_barred" label="Time-barred" theme="red" size="md" />
					<span
						class="text-base"
						:class="row.due.late ? 'font-medium text-ink-red-4' : 'text-ink-gray-6'"
					>
						{{ dueLine }}
					</span>
				</div>
				<p class="text-base text-ink-gray-6">{{ pageDetail }}</p>
				<ol
					v-if="showSteps"
					data-tour="filing-steps"
					class="flex flex-wrap items-center gap-x-2 gap-y-1 pt-1 text-sm"
					aria-label="Where this filing is"
				>
					<li
						v-for="(step, index) in steps.steps"
						:key="step"
						class="flex items-center gap-2"
					>
						<span
							class="flex items-center gap-1.5"
							:class="stepClass(index)"
							:aria-current="index === steps.current ? 'step' : undefined"
						>
							<span :class="stepIcon(index)" class="size-4" aria-hidden="true" />
							{{ step }}
						</span>
						<span
							v-if="index < steps.steps.length - 1"
							class="lucide-chevron-right size-3.5 text-ink-gray-4"
							aria-hidden="true"
						/>
					</li>
				</ol>
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

			<p
				v-if="timeBarNote"
				role="alert"
				class="flex items-start gap-2 rounded-lg bg-surface-red-1 px-4 py-3 text-base text-ink-red-4"
			>
				<span class="lucide-calendar-x mt-0.5 size-4 shrink-0" aria-hidden="true" />
				{{ timeBarNote }}
			</p>

			<section
				v-if="fixedSumText.length"
				class="flex flex-col gap-2 rounded-lg bg-surface-gray-2 px-4 py-3"
				aria-labelledby="fixed-sum-heading"
			>
				<h2 id="fixed-sum-heading" class="text-base font-semibold text-ink-gray-8">
					QRMP payment
				</h2>
				<p v-for="line in fixedSumText" :key="line" class="text-base text-ink-gray-8">
					{{ line }}
				</p>
				<Button
					v-if="fixedSum?.amount && editable"
					class="self-start"
					label="Use this amount"
					@click="useFixedSum"
				/>
			</section>

			<section
				v-if="penaltyText.length"
				class="flex flex-col gap-1 rounded-lg px-4 py-3"
				:class="penalty.days_late ? 'bg-surface-red-1' : 'bg-surface-amber-1'"
				aria-labelledby="penalty-heading"
			>
				<h2 id="penalty-heading" class="text-base font-semibold text-ink-gray-8">
					{{ penalty.days_late ? "Cost of filing late" : "If it is filed late" }}
				</h2>
				<p v-for="line in penaltyText" :key="line" class="text-base text-ink-gray-8">
					{{ line }}
				</p>
				<details v-if="penalty.rule" class="text-sm text-ink-gray-6">
					<summary class="cursor-pointer">The rule</summary>
					<p class="mt-1">{{ penalty.rule }}</p>
					<p class="mt-1">{{ penaltySource }}</p>
				</details>
			</section>

			<section class="flex flex-col gap-4" aria-labelledby="filing-heading">
				<h2 id="filing-heading" class="text-base font-semibold text-ink-gray-8">Filing</h2>

				<template v-if="formShown">
					<FormControl
						v-if="rules?.allows_nil"
						v-model="form.is_nil"
						type="checkbox"
						label="NIL return: nothing to report or pay this period"
						@update:model-value="clearNilAmounts"
					/>
					<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
						<FormControl
							v-model="form.filed_on"
							type="date"
							:format="pickerFormat()"
							label="Filed on"
							placeholder="Pick a date"
							:error="fieldError('Filed on')"
						/>
						<FormControl
							v-model="form.acknowledgement_number"
							:label="declared ? 'Reference (optional)' : 'Acknowledgement number'"
							:placeholder="
								declared ? 'Request number or email' : 'ARN, challan or SRN'
							"
							:error="fieldError('Acknowledgement number')"
						/>
					</div>

					<div class="flex flex-col gap-1.5">
						<span class="text-xs text-ink-gray-5">
							Proof<template v-if="rules?.requires_proof && !declared">
								(needed)</template
							>
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
							v-if="!form.is_nil"
							v-model="form.amount_paid"
							type="number"
							label="Amount paid"
							placeholder="0.00"
						/>
						<FormControl
							v-if="!form.is_nil"
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

				<div
					v-else-if="editable && !inReview"
					class="flex flex-col gap-2 rounded-lg bg-surface-gray-1 px-4 py-3"
				>
					<p class="text-base text-ink-gray-8">{{ howTo }}</p>
					<p v-if="task.remarks" class="text-sm text-ink-gray-6">
						Note: {{ task.remarks }}
					</p>
				</div>

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
				<Button
					v-if="editable && inReview && !formShown"
					class="self-start"
					variant="ghost"
					icon-left="lucide-pencil"
					label="Correct a detail"
					@click="opened = true"
				/>
			</section>

			<section
				v-if="clientLogin || documents.length"
				class="flex flex-col gap-3"
				aria-labelledby="documents-heading"
			>
				<div class="flex items-center justify-between gap-3">
					<h2 id="documents-heading" class="text-base font-semibold text-ink-gray-8">
						Documents
					</h2>
					<template v-if="clientLogin">
						<Button
							icon-left="lucide-upload"
							label="Upload"
							:loading="uploading"
							@click="documentInput?.click()"
						/>
						<input
							ref="documentInput"
							type="file"
							:accept="DOCUMENT_TYPES"
							class="hidden"
							@change="sendDocument"
						/>
					</template>
				</div>
				<p v-if="uploadError" role="alert" class="text-base text-ink-red-4">
					{{ uploadError }}
				</p>
				<p v-if="clientLogin && !documents.length" class="text-base text-ink-gray-5">
					Upload what your firm needs for this filing, such as a sales register or a bank
					statement. They are told when you do.
				</p>
				<ul class="flex flex-col">
					<li v-for="document in documents" :key="document.name">
						<a
							:href="document.file_url"
							target="_blank"
							class="flex items-center gap-3 rounded-lg px-1 py-1.5 hover:bg-surface-gray-2"
						>
							<span
								class="lucide-file-text size-4 shrink-0 text-ink-gray-5"
								aria-hidden="true"
							/>
							<span class="min-w-0 flex-1 truncate text-base text-ink-gray-8">{{
								document.file_name
							}}</span>
							<span class="shrink-0 text-sm text-ink-gray-5">{{
								formatDate(document.creation)
							}}</span>
						</a>
					</li>
				</ul>
			</section>

			<section
				v-if="requests.length || mayAsk"
				class="flex flex-col gap-1"
				aria-labelledby="requests-heading"
			>
				<div class="flex items-center justify-between gap-3 pb-2">
					<h2 id="requests-heading" class="text-base font-semibold text-ink-gray-8">
						{{ clientLogin ? "Documents your firm needs" : "Asked of the client" }}
					</h2>
					<Button
						v-if="mayAsk"
						icon-left="lucide-file-up"
						label="Ask the client"
						@click="asking = true"
					/>
				</div>
				<WorkRow
					v-for="request in requests"
					:key="request.name"
					:row="requestRow(request, { client: clientLogin })"
				/>
			</section>

			<!-- A manager changes who prepares and who reviews it here; the rest is the filing's own. -->
			<EditableDetails
				doctype="Compliance Task"
				:name="name"
				:doc="task"
				:details="FILING_DETAILS"
				:may-edit="mayReassign"
				@saved="load"
			/>
		</template>
	</RecordFrame>

	<AskDocument
		v-if="mayAsk"
		v-model:open="asking"
		:task="props.name"
		:task-label="`${task.obligation_template} (${task.period_label})`"
		:filing-due="task.effective_due_date"
		@created="openRequest"
	/>

	<!-- The actions stay in reach at the foot of the screen, on a phone above the tab bar. -->
	<div
		v-if="footerShown"
		data-tour="filing-actions"
		class="sticky bottom-0 z-10 mt-auto border-t border-outline-gray-1 bg-surface-base"
	>
		<div
			class="mx-auto flex w-full flex-col-reverse gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-end sm:px-6"
			:class="recordWidth(name, { client: clientLogin })"
		>
			<p v-if="footerError" role="alert" class="text-sm text-ink-red-4 sm:mr-auto">
				{{ footerError }}
			</p>
			<!-- Stacked bottom-up on a phone: the main action first, then Send back, then Save. -->
			<Button
				v-if="!formShown && !inReview"
				variant="solid"
				icon-left="lucide-file-pen-line"
				label="Record the filing"
				:size="buttonSize"
				:disabled="waiting"
				@click="startRecording"
			/>
			<Button
				v-if="formShown"
				label="Save"
				:size="buttonSize"
				:loading="busy === 'save'"
				:disabled="Boolean(busy) || waiting || !dirty"
				@click="save()"
			/>
			<Button
				v-if="actions.sendBack"
				label="Send back"
				:size="buttonSize"
				:disabled="Boolean(busy) || waiting"
				@click="sendBack"
			/>
			<Button
				v-if="primary && (formShown || inReview)"
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
import { useRouter } from "vue-router";
import { call, getDoc, getList, uploadClientDocument } from "@/api";
import { boot, isClientLogin, isManager, mayRecord } from "@/boot";
import AskDocument from "@/components/AskDocument.vue";
import WorkRow from "@/components/WorkRow.vue";
import { OPEN_REQUEST_STATUSES, REQUEST_FIELDS, requestRow } from "@/lib/requests";
import { penaltyLines } from "@/lib/score";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import {
	CLOSED_STATUSES,
	FILING_FIELDS,
	changedValues,
	filingSteps,
	formValues,
	NIL_ZERO_FIELDS,
	fixedSumLines,
	missingDetails,
	nilDeclared,
	showFilingForm,
	taskActions,
	taskRow,
} from "@/lib/filings";
import { isoDate } from "@/lib/obligations";
import { TIME_BAR_WARNING_DAYS, daysBetween } from "@/pages/myWork";
import { deskActions } from "@/navigation";
import { SAVED_ON_DEVICE, isWaiting, refresh as refreshOutbox } from "@/offline/outbox";
import { submit } from "@/offline/queue";
import { formatDate, pickerFormat } from "@/lib/format";
import { recordWidth } from "@/lib/records";
import { notLoaded } from "@/offline/reachability";
import { learnNames, nameOf } from "@/composables/usePeople";
import EditableDetails from "@/components/EditableDetails.vue";
import RecordFrame from "@/components/RecordFrame.vue";

const props = defineProps({ name: { type: String, required: true } });

const task = ref(null);

// The band across the top: when it is due, who prepares and who checks it, for which company.
const keyFacts = computed(() => [
	{
		label: "Due",
		icon: "lucide-calendar-clock",
		value: formatDate(task.value.effective_due_date),
		tone: task.value.is_overdue ? "red" : "plain",
	},
	{ label: "Responsible", icon: "lucide-user-round", value: nameOf(task.value.responsible) },
	{ label: "Reviewer", icon: "lucide-user-check", value: nameOf(task.value.reviewer) },
	{ label: "Company", icon: "lucide-building-2", value: task.value.company },
]);
const rules = ref(null);
const error = ref("");
const formError = ref("");
// Set once someone tries to send the filing on; the gaps then show and clear as they are filled.
const checking = ref(false);
const busy = ref("");
// Follows the outbox: true while a change to this filing is kept on the device.
const waiting = computed(() => isWaiting("Compliance Task", props.name));
const proofFile = ref(null);
const fileInput = ref(null);

// Files on the filing other than its proof; a client's login uploads them here.
const DOCUMENT_TYPES = "image/*,application/pdf,.csv,.txt,.doc,.docx,.xls,.xlsx";
const clientLogin = isClientLogin();
const allDocuments = ref([]);
const documents = computed(() =>
	allDocuments.value.filter((document) => document.file_url !== task.value?.proof)
);
const documentInput = ref(null);
const uploading = ref(false);
const uploadError = ref("");

// Documents asked of the client for this filing (CA/CS firms).
const router = useRouter();
const requests = ref([]);

// What filing late costs: shown while the filing is open, and for one filed late.
const penalty = ref(null);
const penaltyText = computed(() => {
	if (!penalty.value || !task.value) return [];
	const open = !CLOSED_STATUSES.includes(task.value.status);
	if (!open && task.value.status !== "Filed Late") return [];
	return penaltyLines(penalty.value, { open });
});
const penaltySource = computed(() => {
	if (penalty.value.set_by_firm) return "Figures set by your firm.";
	if (penalty.value.checked_on) {
		return `Checked by a chartered accountant on ${formatDate(penalty.value.checked_on)}.`;
	}
	return "An estimate from the Act; not yet checked by a chartered accountant.";
});
const asking = ref(false);
const isFirm = boot.accountType === "CA/CS Firm";
const mayAsk = computed(
	() =>
		Boolean(task.value) &&
		isFirm &&
		!clientLogin &&
		mayRecord() &&
		!CLOSED_STATUSES.includes(task.value.status)
);
const openRequest = (request) =>
	router.push({ name: "DocumentRequest", params: { name: request.name } });
const form = reactive(Object.fromEntries(FILING_FIELDS.map((field) => [field, ""])));

const isMobile = useIsMobile();
const buttonSize = computed(() => (isMobile.value ? "md" : "sm"));

const row = computed(() => taskRow(task.value));
// The last day the portal accepts the return: said once it has passed, and in the 90 days before.
const timeBarNote = computed(() => {
	const current = task.value;
	if (!current?.last_filing_date || CLOSED_STATUSES.includes(current.status)) return "";
	if (current.status === "Ready for Review" && !current.is_time_barred) return "";
	const lastDay = formatDate(current.last_filing_date);
	if (current.is_time_barred) {
		return `Time-barred: the portal accepted this return only until ${lastDay}, and no longer does.`;
	}
	const today = new Date();
	const midnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());
	const days = daysBetween(midnight, new Date(`${current.last_filing_date}T00:00:00`));
	if (days < 0 || days > TIME_BAR_WARNING_DAYS) return "";
	const when = days === 0 ? "today" : days === 1 ? "tomorrow" : `in ${days} days`;
	return `Last day to file: ${lastDay}, ${when}. After that the portal no longer accepts this return.`;
});
// The badge already says NIL on this page.
const pageDetail = computed(() =>
	[task.value.period_label, task.value.company].filter(Boolean).join(" · ")
);
const actions = computed(() => taskActions(task.value, rules.value, boot));
const editable = computed(() => actions.value.edit);
const inReview = computed(() => task.value?.status === "Ready for Review");

// The page unfolds as the filing moves on: what to do while it is open, the filing fields once
// someone records it, a summary to check in review, and the record once it is done.
const opened = ref(false);
const formShown = computed(() =>
	task.value
		? showFilingForm(task.value, { editable: editable.value, opened: opened.value })
		: false
);
const footerShown = computed(
	() => editable.value && (formShown.value || !inReview.value || Boolean(primary.value))
);
const steps = computed(() => filingSteps(task.value, rules.value));
const showSteps = computed(
	() => !["Time-barred", "Not Applicable", "Cancelled"].includes(task.value.status)
);
const stepDone = (index) =>
	index < steps.value.current ||
	(index === steps.value.current && CLOSED_STATUSES.includes(task.value.status));
function stepClass(index) {
	if (stepDone(index)) return "text-ink-green-4";
	return index === steps.value.current ? "font-medium text-ink-gray-8" : "text-ink-gray-5";
}
function stepIcon(index) {
	if (stepDone(index)) return "lucide-circle-check";
	return index === steps.value.current ? "lucide-circle-dot" : "lucide-circle";
}
// A NIL period that gives no acknowledgement: the form asks only for the date.
const declared = computed(() => nilDeclared(form, rules.value));
function clearNilAmounts(nil) {
	if (nil) for (const field of NIL_ZERO_FIELDS) form[field] = "";
}
const howTo = computed(() => {
	const rule = rules.value || {};
	const due = formatDate(task.value.effective_due_date);
	if (task.value.is_nil && nilDeclared(task.value, rule)) {
		return `Nothing to report this period. Declare it on the portal (for TDS, the declaration for non-filing on TRACES) by ${due}, then record the date here.`;
	}
	if (task.value.is_nil) {
		return `Nothing to report this period: file ${
			rule.form || task.value.obligation_template
		} as a NIL return by ${due}, then record the date and acknowledgement number here.`;
	}
	const where = rule.authority ? ` with the ${rule.authority}` : "";
	const what = [
		"the date",
		"the acknowledgement number",
		rule.requires_proof && "a copy of the acknowledgement or challan",
		rule.requires_payment && "the amount paid",
	].filter(Boolean);
	const record = `${what.slice(0, -1).join(", ")} and ${what[what.length - 1]}`;
	return `File ${rule.form || task.value.obligation_template}${where} by ${formatDate(
		task.value.effective_due_date
	)}, then record it here: ${record}.`;
});

function startRecording() {
	if (!form.filed_on) form.filed_on = isoDate(new Date());
	opened.value = true;
}
const hasProof = computed(() => Boolean(proofFile.value || task.value?.proof));
const dirty = computed(
	() => Boolean(proofFile.value) || Object.keys(changedValues(form, task.value || {})).length > 0
);
const showAmounts = computed(
	() =>
		// A NIL return still shows its late fee: one filed late pays it.
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

// "Last day to file 15 Jan 2027" reads on after "Due …" without lower-casing the month.
const lowerFirst = (text) => text.charAt(0).toLowerCase() + text.slice(1);
const dueLine = computed(() => {
	const due = `Due ${formatDate(task.value.effective_due_date)}`;
	return row.value.due.text && !row.value.due.text.startsWith("Filed")
		? `${due} · ${lowerFirst(row.value.due.text)}`
		: due;
});

const reviewNote = computed(() => {
	const current = task.value;
	if (current.status !== "Ready for Review") return "";
	if (actions.value.markFiled) {
		return "Check the details and proof, then mark it filed or send it back with a remark.";
	}
	return `Waiting for ${
		nameOf(current.reviewer) || "a Compliance Manager"
	} to check it and mark it filed.`;
});

const proofLabel = computed(() => {
	if (proofFile.value) return proofFile.value.name;
	if (!task.value.proof) return "No proof attached";
	return decodeURIComponent(task.value.proof.split("/").pop());
});

const filingFacts = computed(() =>
	[
		["Return", task.value.is_nil ? "NIL: nothing to report or pay" : ""],
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
		[
			"Reviewed by",
			task.value.filed_without_check
				? `No second check; filed by ${nameOf(task.value.reviewed_by)}`
				: nameOf(task.value.reviewed_by),
		],
		["Remarks", task.value.remarks],
	]
		.filter(([, value]) => value)
		.map(([label, value, href]) => ({ label, value, href }))
);

// The filing's details. Responsible and Reviewer are a manager's to change, where they are shown;
// the others come from the obligation and the company, and show only.
const dueText = (current) =>
	current.extended_due_date
		? `${formatDate(current.extended_due_date)} (extended from ${formatDate(
				current.due_date
		  )})`
		: formatDate(current.due_date);
const FILING_DETAILS = [
	{ field: "period_label", label: "Period", show: (current) => current.period_label },
	{ field: "company", label: "Company", show: (current) => current.company },
	{ field: "law", label: "Law", show: (current) => current.law },
	{
		field: "registration_number",
		label: "Registration",
		show: (current) => current.registration_number,
	},
	{ field: "state", label: "State", show: (current) => current.state },
	{ field: "due_date", label: "Due date", show: dueText },
	{ field: "responsible", label: "Responsible", show: (current) => nameOf(current.responsible) },
	{ field: "reviewer", label: "Reviewer", show: (current) => nameOf(current.reviewer) },
];
const mayReassign = computed(() => isManager() && !isClientLogin());

const menu = computed(() => [
	...deskActions("Compliance Task", props.name),
	...(editable.value && rules.value?.allows_nil
		? [
				task.value.is_nil
					? {
							label: "Not NIL after all",
							icon: "lucide-undo-2",
							onClick: () => setNil(0),
					  }
					: {
							label: "Mark NIL, file later",
							icon: "lucide-circle-dashed",
							onClick: () => setNil(1),
					  },
		  ]
		: []),
	...(editable.value
		? [{ label: "Does not apply", icon: "lucide-circle-slash", onClick: notApplicable }]
		: []),
	...(task.value?.is_time_barred && isManager() && !isClientLogin()
		? [{ label: "Close as time-barred", icon: "lucide-calendar-x", onClick: closeTimeBarred }]
		: []),
]);

// Nothing to report this period: the filing stays open, due date and late fee and all, as a NIL
// return to file later (alone, or with others on the NIL page).
function setNil(nil) {
	const values = { is_nil: nil };
	if (nil) {
		for (const field of NIL_ZERO_FIELDS) if (Number(task.value[field])) values[field] = 0;
	}
	return send(values, "nil");
}

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
	opened.value = false;
	checking.value = false;
	formError.value = "";
}

async function loadDocuments() {
	try {
		allDocuments.value = await call("kxcompliance.api.documents", {
			doctype: "Compliance Task",
			name: props.name,
		});
	} catch {
		// Documents are extra; the filing is still useful without them, offline included.
		allDocuments.value = [];
	}
}

// The QRMP fixed sum, for a PMT-06 filing still to pay.
const fixedSum = ref(null);
const fixedSumText = computed(() =>
	task.value && !CLOSED_STATUSES.includes(task.value.status) ? fixedSumLines(fixedSum.value) : []
);
async function loadFixedSum() {
	fixedSum.value = null;
	if (rules.value?.form !== "PMT-06") return;
	try {
		fixedSum.value = await call("kxcompliance.api.fixed_sum", { task: props.name });
	} catch {
		// The fixed sum is a help; the filing is still useful without it, offline included.
		fixedSum.value = null;
	}
}
function useFixedSum() {
	startRecording();
	form.amount_paid = fixedSum.value.amount;
}

async function loadPenalty() {
	try {
		penalty.value = await call("kxcompliance.api.filing_penalty", { task: props.name });
	} catch {
		// The estimate is extra; the filing is still useful without it, offline included.
		penalty.value = null;
	}
}

async function loadRequests() {
	if (!isFirm) return;
	try {
		requests.value = (
			await getList("Document Request", {
				fields: REQUEST_FIELDS,
				filters: [
					["compliance_task", "=", props.name],
					["status", "in", [...OPEN_REQUEST_STATUSES, "Accepted"]],
				],
				orderBy: "due_date asc",
				limit: 20,
			})
		).rows;
	} catch {
		// Requests are extra here; the filing page works without them, offline included.
		requests.value = [];
	}
}

async function sendDocument(event) {
	const file = event.target.files?.[0];
	event.target.value = "";
	if (!file) return;
	uploading.value = true;
	uploadError.value = "";
	try {
		await uploadClientDocument(file, props.name);
		toast.success(`${file.name} uploaded`);
		await loadDocuments();
	} catch (err) {
		uploadError.value = err.isNetwork
			? "The upload did not reach the server. Try again when you are back online."
			: err.message;
	} finally {
		uploading.value = false;
	}
}

async function load() {
	error.value = "";
	try {
		task.value = await getDoc("Compliance Task", props.name);
		learnNames([task.value.responsible, task.value.reviewer, task.value.reviewed_by]);
		rules.value = await getDoc(
			"Compliance Obligation Template",
			task.value.obligation_template
		);
		fillForm();
		loadFixedSum();
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
			toast.info(SAVED_ON_DEVICE);
		} else {
			toast.success(
				{ "Ready for Review": "Sent for review", Filed: "Marked filed" }[values.status] ||
					"Saved"
			);
			await Promise.all([load(), loadPenalty()]);
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
		message: `${nameOf(
			task.value.responsible
		)} gets it back to correct. Say what needs to change.`,
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

// A manager closes a filing the portal no longer accepts, saying why it was not filed in time.
function closeTimeBarred() {
	dialog.prompt({
		title: "Close as time-barred",
		message: `The portal accepted this return only until ${formatDate(
			task.value.last_filing_date
		)}. The filing is closed as time-barred with your reason, and still counts in the compliance score for a year.`,
		confirmLabel: "Close filing",
		fields: [
			{
				name: "remarks",
				label: "Why it was not filed in time",
				type: "textarea",
				required: true,
				defaultValue: form.remarks,
			},
		],
		onConfirm: async ({ values }) => {
			await send({ remarks: values.remarks, status: "Time-barred" }, "barred");
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

// Once a change kept on the device has been sent, show the filing as the server has it.
watch(waiting, (now, before) => {
	if (before && !now) load();
});
watch(
	() => props.name,
	() => {
		load();
		loadDocuments();
		loadRequests();
		loadPenalty();
	}
);
onMounted(() => {
	load();
	loadDocuments();
	loadRequests();
	loadPenalty();
});
</script>
