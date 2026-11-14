<template>
	<AppPageHeader
		title="File in bulk"
		:parent="{ label: 'Filings', route: { name: 'Filings' } }"
	/>

	<div class="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6 sm:px-6">
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<Skeleton v-else-if="!choices" class="h-10 w-full rounded-lg" />

		<template v-else>
			<p class="text-base text-ink-gray-6">
				Pick a return and period to see every open filing for it. Set the date once, add
				each company's acknowledgement number and proof, and save them together.
			</p>
			<FormControl
				v-model="chosen"
				data-tour="bulk-choose"
				type="select"
				label="Return and period"
				:options="[
					{
						label: choices.length
							? 'Choose a return and period'
							: 'Nothing open to file',
						value: '',
					},
					...choices.map((choice) => ({
						label: choiceLabel(choice),
						value: choiceKey(choice),
					})),
				]"
			/>

			<Skeleton v-if="loadingRows" class="h-48 w-full rounded-lg" />

			<template v-else-if="rows.length">
				<div class="flex flex-col gap-3 sm:flex-row sm:items-end">
					<FormControl
						v-model="sharedDate"
						data-tour="bulk-date"
						class="sm:w-56"
						type="date"
						:format="pickerFormat()"
						label="Filed on"
						description="For every row without its own date."
					/>
					<div
						v-if="rules?.requires_proof"
						class="flex flex-col gap-1 sm:flex-1"
						data-tour="bulk-proofs"
					>
						<Button
							class="self-start"
							icon-left="lucide-files"
							label="Add proofs for many"
							@click="manyInput.click()"
						/>
						<p class="text-sm text-ink-gray-5">
							Each file goes to the row whose GSTIN, TAN or acknowledgement number is
							in its name.
						</p>
						<input
							ref="manyInput"
							type="file"
							multiple
							accept="image/*,application/pdf"
							class="hidden"
							@change="dropMany"
						/>
					</div>
				</div>
				<p
					v-if="leftOver.length"
					class="rounded-lg bg-surface-amber-1 px-3 py-2 text-sm text-ink-amber-4"
				>
					Not matched to a row, so attach them by hand: {{ leftOver.join(", ") }}
				</p>

				<div class="flex items-center gap-3 border-b border-outline-gray-1 pb-2">
					<FormControl
						:model-value="allTicked"
						type="checkbox"
						label="All that can be saved"
						@update:model-value="tickAll"
					/>
				</div>

				<ul class="flex flex-col" data-tour="bulk-rows">
					<li
						v-for="row in rows"
						:key="row.name"
						class="flex flex-col gap-3 border-b border-outline-gray-1 py-3 xl:flex-row xl:items-start"
						:class="row.result?.state === 'saved' && 'opacity-60'"
					>
						<div class="flex min-w-0 items-start gap-3 xl:w-64 xl:shrink-0">
							<FormControl
								v-model="row.ticked"
								type="checkbox"
								:disabled="!row.step.status || row.result?.state === 'saved'"
								:aria-label="`Save ${row.company}`"
							/>
							<span class="flex min-w-0 flex-col">
								<RouterLink
									:to="{ name: 'ComplianceTask', params: { name: row.name } }"
									class="truncate text-base font-medium text-ink-gray-8 hover:underline"
									>{{ row.company }}</RouterLink
								>
								<span class="truncate text-sm text-ink-gray-5">{{
									[
										row.registration_number,
										row.result?.state === "saved" ? "" : row.step.label,
									]
										.filter(Boolean)
										.join(" · ")
								}}</span>
							</span>
						</div>
						<div
							v-if="row.step.status && row.result?.state !== 'saved'"
							class="grid flex-1 grid-cols-1 gap-2"
							:class="
								rules?.requires_payment
									? 'sm:grid-cols-[1fr_9rem_auto]'
									: 'sm:grid-cols-[1fr_auto]'
							"
						>
							<FormControl
								v-model="row.acknowledgement_number"
								:aria-label="`Acknowledgement number for ${row.company}`"
								placeholder="Acknowledgement number"
							/>
							<FormControl
								v-if="rules?.requires_payment"
								v-model="row.amount_paid"
								type="number"
								:aria-label="`Amount paid for ${row.company}`"
								placeholder="Amount paid"
							/>
							<div class="flex min-w-0 items-center gap-2">
								<Button
									:icon-left="
										row.proofFile || row.proof
											? 'lucide-file-check'
											: 'lucide-paperclip'
									"
									:label="proofLabel(row)"
									:aria-label="`Proof for ${row.company}`"
									class="max-w-[14rem]"
									@click="pickFor(row)"
								/>
							</div>
						</div>
						<p
							v-if="row.result"
							class="text-sm xl:w-48"
							:class="
								row.result.state === 'error'
									? 'text-ink-red-4'
									: 'text-ink-green-4'
							"
							:role="row.result.state === 'error' ? 'alert' : undefined"
						>
							{{ row.result.message }}
						</p>
					</li>
				</ul>
				<input
					ref="oneInput"
					type="file"
					accept="image/*,application/pdf"
					class="hidden"
					@change="pickOne"
				/>
			</template>

			<p v-else-if="chosen" class="py-10 text-center text-base text-ink-gray-5">
				Nothing left to file for this return and period.
			</p>
		</template>
	</div>

	<div
		v-if="rows.length"
		class="sticky bottom-0 z-10 mt-auto border-t border-outline-gray-1 bg-surface-base"
	>
		<div
			class="mx-auto flex w-full max-w-5xl flex-col-reverse gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-end sm:px-6"
		>
			<p v-if="progress" class="text-sm text-ink-gray-6 sm:mr-auto" aria-live="polite">
				{{ progress }}
			</p>
			<Button
				variant="solid"
				data-tour="bulk-save"
				:label="saveLabel(ticked.map((row) => row.step.status))"
				:disabled="!ticked.length"
				:loading="saving"
				@click="saveAll"
			/>
		</div>
	</div>
</template>

<script setup>
// One return for many companies: open filings for a return and period in one table, saved together.
// Each row is saved on its own as the filing page saves it, so one row's problem does not stop the rest.
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { Button, FormControl, Skeleton, toast } from "frappe-ui";
import { call, getDoc, getList } from "@/api";
import { boot } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import {
	BULK_FIELDS,
	BULK_STATUSES,
	choiceLabel,
	matchFiles,
	nextStep,
	rowMissing,
	rowValues,
	saveLabel,
} from "@/lib/bulkFiling";
import { pickerFormat } from "@/lib/format";
import { isoDate } from "@/lib/obligations";
import { SAVED_ON_DEVICE, refresh as refreshOutbox } from "@/offline/outbox";
import { submit } from "@/offline/queue";
import { notLoaded } from "@/offline/reachability";

const route = useRoute();
const router = useRouter();
const choices = ref(null);
const error = ref("");
const chosen = ref("");
const rules = ref(null);
const rows = ref([]);
const loadingRows = ref(false);
const sharedDate = ref(isoDate(new Date()));
const leftOver = ref([]);
const saving = ref(false);
const progress = ref("");
const manyInput = ref(null);
const oneInput = ref(null);
let pickingRow = null;

const person = { user: boot.user, roles: boot.roles };
const choiceKey = (choice) => `${choice.obligation_template}|${choice.period_end}`;
const ticked = computed(() => rows.value.filter((row) => row.ticked && row.step.status));
const saveable = computed(() =>
	rows.value.filter((row) => row.step.status && row.result?.state !== "saved")
);
const allTicked = computed(
	() => saveable.value.length > 0 && saveable.value.every((row) => row.ticked)
);

function tickAll(value) {
	for (const row of saveable.value) row.ticked = Boolean(value);
}

function proofLabel(row) {
	if (row.proofFile) return row.proofFile.name;
	if (row.proof) return decodeURIComponent(row.proof.split("/").pop());
	return rules.value?.requires_proof ? "Attach proof" : "Proof (optional)";
}

function pickFor(row) {
	pickingRow = row;
	oneInput.value.click();
}

function pickOne(event) {
	const file = event.target.files?.[0];
	event.target.value = "";
	if (file && pickingRow) pickingRow.proofFile = file;
	pickingRow = null;
}

function dropMany(event) {
	const files = [...(event.target.files || [])];
	event.target.value = "";
	const open = rows.value.filter((row) => row.step.status && row.result?.state !== "saved");
	const { matched, unmatched } = matchFiles(files, open);
	for (const row of open) if (matched[row.name]) row.proofFile = matched[row.name];
	leftOver.value = unmatched.map((file) => file.name);
}

async function loadRows() {
	rows.value = [];
	leftOver.value = [];
	progress.value = "";
	const [template, periodEnd] = chosen.value.split("|");
	router.replace({ query: chosen.value ? { return: template, period: periodEnd } : {} });
	if (!chosen.value) return;
	loadingRows.value = true;
	error.value = "";
	try {
		const [doc, list] = await Promise.all([
			getDoc("Compliance Obligation Template", template),
			getList("Compliance Task", {
				fields: BULK_FIELDS,
				filters: [
					["obligation_template", "=", template],
					["period_end", "=", periodEnd],
					["status", "in", BULK_STATUSES],
				],
				orderBy: "company asc",
				limit: 500,
			}),
		]);
		rules.value = doc;
		rows.value = list.rows.map((row) => {
			const step = nextStep(row, doc, person);
			return {
				...row,
				acknowledgement_number: row.acknowledgement_number || "",
				amount_paid: Number(row.amount_paid) || "",
				proofFile: null,
				step,
				ticked: Boolean(step.status),
				result: null,
			};
		});
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("these filings") : err.message;
	} finally {
		loadingRows.value = false;
	}
}

async function saveRow(row) {
	const missing = rowMissing(row, sharedDate.value, rules.value, Boolean(row.proofFile));
	if (missing.length) {
		row.result = { state: "error", message: `Fill in ${missing.join(", ")}.` };
		return "error";
	}
	try {
		const result = await submit({
			doctype: "Compliance Task",
			name: row.name,
			values: { ...rowValues(row, sharedDate.value, rules.value), status: row.step.status },
			baseModified: row.modified,
			files: row.proofFile
				? [{ field: "proof", blob: row.proofFile, fileName: row.proofFile.name }]
				: [],
		});
		const message = result.queued
			? SAVED_ON_DEVICE
			: row.step.status === "Filed"
			? "Filed"
			: "Sent for review";
		row.result = { state: "saved", message };
		row.ticked = false;
		return "saved";
	} catch (err) {
		row.result = { state: "error", message: err.message };
		return "error";
	}
}

async function saveAll() {
	saving.value = true;
	const batch = [...ticked.value];
	const counts = { saved: 0, error: 0 };
	for (const [index, row] of batch.entries()) {
		progress.value = `Saving ${index + 1} of ${batch.length}…`;
		counts[await saveRow(row)] += 1;
	}
	saving.value = false;
	await refreshOutbox();
	progress.value = counts.error
		? `${counts.saved} saved; ${counts.error} need a look (marked in red).`
		: `${counts.saved} saved.`;
	if (counts.saved) toast.success(`${counts.saved} saved`);
}

watch(chosen, loadRows);

onMounted(async () => {
	try {
		choices.value = await call("kxcompliance.api.bulk_filing_choices");
		const { return: template, period } = route.query;
		const wanted = choices.value.find(
			(choice) => choice.obligation_template === template && choice.period_end === period
		);
		if (wanted) chosen.value = choiceKey(wanted);
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("the returns to file") : err.message;
	}
});
</script>
