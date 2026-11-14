<template>
	<AppPageHeader title="Bulk setup" />

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6 sm:px-6">
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>

		<template v-if="!sheet">
			<p class="text-base text-ink-gray-7">
				Set up many clients and companies at once from a spreadsheet, one row per company.
				Every row is checked and shown to you before anything is made.
			</p>
			<ol class="flex flex-col gap-4">
				<li class="flex items-start gap-3">
					<span
						class="flex size-7 shrink-0 items-center justify-center rounded-full bg-surface-gray-2 text-sm font-medium text-ink-gray-7"
						>1</span
					>
					<div class="flex flex-1 flex-col gap-2">
						<p class="text-base text-ink-gray-8">
							Download the template and fill in a row for each company: its client,
							kind, who handles it, and its registrations. GSTINs can be listed
							together; their states are read from the numbers.
						</p>
						<div>
							<Button
								icon-left="lucide-download"
								label="Download template"
								href="/api/method/compliance_plus.api.setup_template"
							/>
						</div>
					</div>
				</li>
				<li class="flex items-start gap-3">
					<span
						class="flex size-7 shrink-0 items-center justify-center rounded-full bg-surface-gray-2 text-sm font-medium text-ink-gray-7"
						>2</span
					>
					<div class="flex flex-1 flex-col gap-2">
						<p class="text-base text-ink-gray-8">
							Upload it as .xlsx or .csv. Companies already set up are left as they
							are, and clients are not emailed.
						</p>
						<div>
							<Button
								variant="solid"
								icon-left="lucide-upload"
								label="Upload sheet"
								:loading="busy"
								@click="input?.click()"
							/>
						</div>
					</div>
				</li>
			</ol>
		</template>

		<template v-else>
			<section class="flex flex-col gap-2">
				<div class="flex flex-wrap items-center gap-2">
					<Badge :label="sheet.status" :theme="statusTheme" size="md" />
					<span class="text-base text-ink-gray-7">{{ line }}</span>
				</div>
				<p v-if="running" class="text-sm text-ink-gray-5">
					This runs on the server; you can leave this page and come back.
				</p>
			</section>

			<ul class="flex flex-col">
				<li
					v-for="row in rows"
					:key="row.name"
					class="flex flex-col gap-1 border-b border-outline-gray-1 py-3 last:border-b-0"
				>
					<div class="flex items-start gap-3">
						<span class="w-10 shrink-0 pt-0.5 text-sm text-ink-gray-5"
							>Row {{ row.row_number }}</span
						>
						<span class="flex min-w-0 flex-1 flex-col gap-0.5">
							<span class="truncate text-base font-medium text-ink-gray-8">{{
								row.company || "No company named"
							}}</span>
							<span v-if="row.client" class="truncate text-sm text-ink-gray-5">{{
								row.client
							}}</span>
						</span>
						<Badge :label="row.outcome" :theme="OUTCOME_THEMES[row.outcome]" />
					</div>
					<p
						class="pl-13 text-sm"
						:class="
							['Error', 'Failed'].includes(row.outcome)
								? 'text-ink-red-4'
								: 'text-ink-gray-6'
						"
					>
						{{ row.message }}
					</p>
				</li>
			</ul>
		</template>

		<input ref="input" type="file" accept=".xlsx,.csv" class="hidden" @change="checkSheet" />
	</div>

	<div
		v-if="sheet && !running"
		class="sticky bottom-0 z-10 mt-auto border-t border-outline-gray-1 bg-surface-base"
	>
		<div
			class="mx-auto flex w-full max-w-3xl flex-col-reverse gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-end sm:px-6"
		>
			<Button
				v-if="sheet.status === 'Checked'"
				label="Upload another sheet"
				:disabled="busy"
				@click="startOver"
			/>
			<Button
				v-if="sheet.status === 'Checked'"
				variant="solid"
				:label="importLabel"
				:loading="busy"
				:disabled="!summary.ready"
				@click="startImport"
			/>
			<Button v-else variant="solid" label="See clients" :route="{ name: 'Clients' }" />
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Badge, Button } from "frappe-ui";
import { createDoc, getDoc, runMethod, upload } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import {
	OUTCOME_THEMES,
	RUNNING_STATUSES,
	importSummary,
	sortedRows,
	summaryLine,
} from "@/lib/bulkSetup";

const STATUS_THEMES = {
	Checked: "blue",
	Queued: "gray",
	Importing: "blue",
	Done: "green",
	"Done with Errors": "amber",
	Failed: "red",
};
const POLL_MS = 3000;

const route = useRoute();
const router = useRouter();
const input = ref(null);
const sheet = ref(null);
const busy = ref(false);
const error = ref("");
let timer;

const rows = computed(() => sortedRows(sheet.value?.rows || []));
const summary = computed(() => importSummary(sheet.value?.rows || []));
const running = computed(() => RUNNING_STATUSES.includes(sheet.value?.status));
const statusTheme = computed(() => STATUS_THEMES[sheet.value?.status] || "gray");
const line = computed(() => summaryLine(summary.value, sheet.value.status));
const importLabel = computed(() =>
	summary.value.ready === 1 ? "Set up 1 company" : `Set up ${summary.value.ready} companies`
);

const friendly = (err, what) =>
	err.isNetwork
		? `${what} did not reach the server. Try again when you are back online.`
		: err.message;

async function load(name) {
	sheet.value = await getDoc("Compliance Setup Import", name);
	clearTimeout(timer);
	// While the import runs on the server, look again every few seconds.
	if (running.value) timer = setTimeout(() => load(name).catch(() => {}), POLL_MS);
}

async function checkSheet(event) {
	const file = event.target.files?.[0];
	event.target.value = "";
	if (!file) return;
	busy.value = true;
	error.value = "";
	try {
		const created = await createDoc("Compliance Setup Import", {});
		await upload(file, { doctype: "Compliance Setup Import", docname: created.name });
		await runMethod("Compliance Setup Import", created.name, "check_sheet");
		await router.replace({ query: { sheet: created.name } });
		await load(created.name);
	} catch (err) {
		error.value = friendly(err, "The sheet");
	} finally {
		busy.value = false;
	}
}

async function startImport() {
	busy.value = true;
	error.value = "";
	try {
		await runMethod("Compliance Setup Import", sheet.value.name, "start_import");
		await load(sheet.value.name);
	} catch (err) {
		error.value = friendly(err, "The import");
	} finally {
		busy.value = false;
	}
}

function startOver() {
	sheet.value = null;
	router.replace({ query: {} });
	input.value?.click();
}

onMounted(async () => {
	if (!route.query.sheet) return;
	try {
		await load(route.query.sheet);
	} catch (err) {
		error.value = friendly(err, "This import");
	}
});
onUnmounted(() => clearTimeout(timer));
</script>
