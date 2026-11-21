<template>
	<AppPageHeader
		title="File NIL returns together"
		:parent="{ label: 'Filings', route: { name: 'Filings' } }"
	/>

	<div class="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6 sm:px-6">
		<!-- One client's companies, or every client's. -->
		<ClientPicker />
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
				Filings marked NIL wait here until they are filed. Pick a company to see them all,
				each return's periods oldest first, as GST files them in order. Set the date once,
				add each acknowledgement, and save them together.
			</p>
			<FormControl
				v-model="chosen"
				data-tour="nil-choose"
				type="select"
				label="Company"
				:options="[
					{
						label: choices.length ? 'Choose a company' : 'No NIL returns to file',
						value: '',
					},
					...choices.map((choice) => ({
						label: nilChoiceLabel(choice),
						value: choice.company,
					})),
				]"
			/>

			<Skeleton v-if="loadingRows" class="h-48 w-full rounded-lg" />

			<template v-else-if="rows.length">
				<FormControl
					v-model="sharedDate"
					data-tour="nil-date"
					class="sm:w-56"
					type="date"
					:format="pickerFormat()"
					label="Filed on"
					description="For every row without its own date."
				/>

				<div class="flex items-center gap-3 border-b border-outline-gray-1 pb-2">
					<FormControl
						:model-value="allTicked"
						type="checkbox"
						label="All that can be saved"
						@update:model-value="tickAll"
					/>
				</div>

				<ul class="flex flex-col" data-tour="nil-rows">
					<li
						v-for="row in rows"
						:key="row.name"
						class="flex flex-col gap-3 border-b border-outline-gray-1 py-3 xl:flex-row xl:items-start"
						:class="row.result?.state === 'saved' && 'opacity-60'"
					>
						<div class="flex min-w-0 items-start gap-3 xl:w-80 xl:shrink-0">
							<FormControl
								v-model="row.ticked"
								type="checkbox"
								:disabled="!row.step.status || row.result?.state === 'saved'"
								:aria-label="`Save ${row.obligation_template}, ${row.period_label}`"
							/>
							<span class="flex min-w-0 flex-col">
								<RouterLink
									:to="{ name: 'ComplianceTask', params: { name: row.name } }"
									class="truncate text-base font-medium text-ink-gray-8 hover:underline"
									>{{ row.obligation_template }}</RouterLink
								>
								<span
									class="truncate text-sm"
									:class="row.late ? 'text-ink-red-4' : 'text-ink-gray-5'"
									>{{ rowLine(row) }}</span
								>
							</span>
						</div>
						<div
							v-if="row.step.status && row.result?.state !== 'saved'"
							class="grid flex-1 grid-cols-1 gap-2 sm:grid-cols-[1fr_auto]"
						>
							<FormControl
								v-model="row.acknowledgement_number"
								:aria-label="`Acknowledgement number for ${row.obligation_template}, ${row.period_label}`"
								:placeholder="
									nilDeclared(row, rulesOf(row))
										? 'Reference (optional)'
										: 'Acknowledgement number'
								"
							/>
							<Button
								:icon-left="
									row.proofFile || row.proof
										? 'lucide-file-check'
										: 'lucide-paperclip'
								"
								:label="proofLabel(row)"
								:aria-label="`Proof for ${row.obligation_template}, ${row.period_label}`"
								class="max-w-[14rem]"
								@click="pickFor(row)"
							/>
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
				No NIL returns left to file for this company.
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
				data-tour="nil-save"
				:label="saveLabel(ticked.map((row) => row.step.status))"
				:disabled="!ticked.length"
				:loading="saving"
				@click="saveAll"
			/>
		</div>
	</div>
</template>

<script setup>
// One company's NIL returns, filed together after the fact: every open filing marked NIL, saved
// one by one in period order, as the filing page saves each.
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { Button, FormControl, Skeleton, toast } from "frappe-ui";
import { call, getDoc, getList } from "@/api";
import { boot } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import ClientPicker from "@/components/ClientPicker.vue";
import {
	BULK_FIELDS,
	BULK_STATUSES,
	nextStep,
	nilChoiceLabel,
	nilOrder,
	rowMissing,
	rowValues,
	saveLabel,
} from "@/lib/bulkFiling";
import { nilDeclared } from "@/lib/filings";
import { formatDate, pickerFormat } from "@/lib/format";
import { isoDate } from "@/lib/obligations";
import { SAVED_ON_DEVICE, refresh as refreshOutbox } from "@/offline/outbox";
import { submit } from "@/offline/queue";
import { notLoaded } from "@/offline/reachability";
import { chosenCompanies, loadClients } from "@/stores/clientFilter";

const route = useRoute();
const router = useRouter();
const choices = ref(null);
const error = ref("");
const chosen = ref("");
const rulesByTemplate = ref({});
const rows = ref([]);
const loadingRows = ref(false);
const sharedDate = ref(isoDate(new Date()));
const saving = ref(false);
const progress = ref("");
const oneInput = ref(null);
let pickingRow = null;

const person = { user: boot.user, roles: boot.roles };
const rulesOf = (row) => rulesByTemplate.value[row.obligation_template];
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

function rowLine(row) {
	const parts = [row.period_label, `due ${formatDate(row.effective_due_date)}`];
	if (row.result?.state !== "saved") parts.push(row.step.label);
	return parts.join(" · ");
}

function proofLabel(row) {
	if (row.proofFile) return row.proofFile.name;
	if (row.proof) return decodeURIComponent(row.proof.split("/").pop());
	const rules = rulesOf(row);
	return rules?.requires_proof && !nilDeclared(row, rules) ? "Attach proof" : "Proof (optional)";
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

async function loadRows() {
	rows.value = [];
	progress.value = "";
	router.replace({ query: chosen.value ? { company: chosen.value } : {} });
	if (!chosen.value) return;
	loadingRows.value = true;
	error.value = "";
	try {
		const list = await getList("Compliance Task", {
			fields: BULK_FIELDS,
			filters: [
				["company", "=", chosen.value],
				["is_nil", "=", 1],
				["status", "in", BULK_STATUSES],
			],
			orderBy: "period_end asc",
			limit: 500,
		});
		const templates = [...new Set(list.rows.map((row) => row.obligation_template))];
		const docs = await Promise.all(
			templates.map((template) => getDoc("Compliance Obligation Template", template))
		);
		rulesByTemplate.value = Object.fromEntries(docs.map((doc) => [doc.name, doc]));
		const today = isoDate(new Date());
		rows.value = nilOrder(list.rows).map((row) => {
			const step = nextStep(row, rulesOf(row), person);
			return {
				...row,
				acknowledgement_number: row.acknowledgement_number || "",
				is_nil: true,
				late: String(row.effective_due_date) < today,
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
	const rules = rulesOf(row);
	const missing = rowMissing(row, sharedDate.value, rules, Boolean(row.proofFile));
	if (missing.length) {
		row.result = { state: "error", message: `Fill in ${missing.join(", ")}.` };
		return "error";
	}
	try {
		const result = await submit({
			doctype: "Compliance Task",
			name: row.name,
			values: { ...rowValues(row, sharedDate.value, rules), status: row.step.status },
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
	// Already in period order; once a return's period fails, its later ones would be refused.
	const batch = [...ticked.value];
	const counts = { saved: 0, error: 0 };
	const held = new Set();
	for (const [index, row] of batch.entries()) {
		progress.value = `Saving ${index + 1} of ${batch.length}…`;
		if (held.has(row.obligation_template)) {
			row.result = { state: "error", message: "File the earlier period first." };
			counts.error += 1;
			continue;
		}
		const outcome = await saveRow(row);
		counts[outcome] += 1;
		if (outcome === "error" && rulesOf(row)?.files_in_order) held.add(row.obligation_template);
	}
	saving.value = false;
	await refreshOutbox();
	progress.value = counts.error
		? `${counts.saved} saved; ${counts.error} need a look (marked in red).`
		: `${counts.saved} saved.`;
	if (counts.saved) toast.success(`${counts.saved} saved`);
}

watch(chosen, loadRows);

async function loadChoices() {
	const params = chosenCompanies.value ? { companies: chosenCompanies.value } : {};
	choices.value = await call("kxcompliance.api.nil_filing_choices", params);
}

// Another client: its own companies to choose from, and the chosen one's filings again.
watch(chosenCompanies, async () => {
	try {
		await loadChoices();
		if (!choices.value.some((choice) => choice.company === chosen.value)) chosen.value = "";
		else loadRows();
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("the NIL returns to file") : err.message;
	}
});

onMounted(async () => {
	try {
		await loadClients();
		await loadChoices();
		const wanted = choices.value.find((choice) => choice.company === route.query.company);
		if (wanted) chosen.value = wanted.company;
		else if (choices.value.length === 1) chosen.value = choices.value[0].company;
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("the NIL returns to file") : err.message;
	}
});
</script>
