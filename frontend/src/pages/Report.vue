<template>
	<AppPageHeader
		:title="report?.title || 'Report'"
		:parent="{ label: 'Reports', route: { name: 'Reports' } }"
	>
		<template v-if="report && rows.length" #actions>
			<Dropdown :options="downloads" align="end">
				<Button
					icon-left="lucide-download"
					:label="isMobile ? undefined : 'Download'"
					:icon="isMobile ? 'lucide-download' : undefined"
					aria-label="Download"
					data-tour="report-download"
				/>
			</Dropdown>
		</template>
	</AppPageHeader>

	<div class="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-6 sm:px-6">
		<p v-if="!report" class="text-base text-ink-gray-6">There is no such report.</p>
		<template v-else>
			<p class="text-base text-ink-gray-6">{{ report.about }}</p>

			<div
				class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4"
				data-tour="report-filters"
			>
				<template v-for="filter in shownFilters" :key="filter.fieldname">
					<FormControl
						v-if="filter.type === 'date'"
						v-model="values[filter.fieldname]"
						type="date"
						:format="pickerFormat()"
						:label="filter.required ? filter.label : `${filter.label} (any)`"
					/>
					<FormControl
						v-else-if="filter.type === 'text'"
						v-model="values[filter.fieldname]"
						:label="filter.label"
						placeholder="Any"
					/>
					<FormControl
						v-else
						v-model="values[filter.fieldname]"
						type="select"
						:label="filter.label"
						:options="optionsFor(filter)"
					/>
				</template>
			</div>

			<p
				v-if="error"
				role="alert"
				class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
			>
				{{ error }}
			</p>
			<p v-else-if="missing.length" class="text-base text-ink-gray-5">
				Choose {{ missing.map((filter) => filter.label.toLowerCase()).join(" and ") }} to
				run the report.
			</p>
			<Skeleton v-else-if="loading && !rows.length" class="h-48 w-full rounded-lg" />
			<p v-else-if="ran && !rows.length" class="py-10 text-center text-base text-ink-gray-5">
				Nothing for these filters.
			</p>

			<template v-else-if="rows.length">
				<p class="text-sm text-ink-gray-5" aria-live="polite">
					{{ rows.length }} {{ rows.length === 1 ? "row" : "rows" }}
				</p>

				<!-- Phones: a card per row. -->
				<ul v-if="isMobile" class="flex flex-col gap-2" data-tour="report-table">
					<li
						v-for="(row, index) in sorted"
						:key="index"
						class="flex flex-col gap-1 rounded-lg border border-outline-gray-1 px-3 py-2.5"
					>
						<component
							:is="
								linkRoute(columns[0], row[columns[0].fieldname])
									? RouterLink
									: 'span'
							"
							:to="linkRoute(columns[0], row[columns[0].fieldname])"
							class="text-base font-medium text-ink-gray-8"
							>{{ cellText(columns[0], row) }}</component
						>
						<dl class="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-sm">
							<template v-for="column in columns.slice(1)" :key="column.fieldname">
								<template v-if="cellText(column, row)">
									<dt class="text-ink-gray-5">{{ column.label }}</dt>
									<dd class="text-ink-gray-8">{{ cellText(column, row) }}</dd>
								</template>
							</template>
						</dl>
					</li>
				</ul>

				<!-- Computers: a table, sorted by any column. -->
				<div
					v-else
					class="overflow-x-auto rounded-lg border border-outline-gray-1"
					data-tour="report-table"
				>
					<table class="w-full text-left text-sm">
						<thead class="bg-surface-gray-1 text-ink-gray-6">
							<tr>
								<th
									v-for="column in columns"
									:key="column.fieldname"
									scope="col"
									class="whitespace-nowrap px-3 py-2 font-medium"
									:class="isNumber(column) ? 'text-right' : ''"
									:aria-sort="
										sortBy === column.fieldname
											? descending
												? 'descending'
												: 'ascending'
											: undefined
									"
								>
									<button
										type="button"
										class="inline-flex items-center gap-1 hover:text-ink-gray-8"
										@click="sortOn(column.fieldname)"
									>
										{{ column.label }}
										<span
											v-if="sortBy === column.fieldname"
											:class="
												descending
													? 'lucide-arrow-down'
													: 'lucide-arrow-up'
											"
											class="size-3"
											aria-hidden="true"
										/>
									</button>
								</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="(row, index) in sorted"
								:key="index"
								class="border-t border-outline-gray-1"
							>
								<td
									v-for="column in columns"
									:key="column.fieldname"
									class="whitespace-nowrap px-3 py-2 text-ink-gray-8"
									:class="isNumber(column) ? 'text-right tabular-nums' : ''"
								>
									<RouterLink
										v-if="linkRoute(column, row[column.fieldname])"
										:to="linkRoute(column, row[column.fieldname])"
										class="underline decoration-outline-gray-3 underline-offset-2"
										>{{ cellText(column, row) }}</RouterLink
									>
									<template v-else>{{ cellText(column, row) }}</template>
								</td>
							</tr>
						</tbody>
						<tfoot v-if="total">
							<tr class="border-t-2 border-outline-gray-2 font-medium">
								<td
									v-for="(column, index) in columns"
									:key="column.fieldname"
									class="whitespace-nowrap px-3 py-2 text-ink-gray-9"
									:class="isNumber(column) ? 'text-right tabular-nums' : ''"
								>
									{{ index === 0 ? "Total" : cellText(column, total) }}
								</td>
							</tr>
						</tfoot>
					</table>
				</div>
			</template>
		</template>
	</div>
</template>

<script setup>
// One report: its filters, the same results the Desk shows, sorted by any column, and a download.
// The filters are kept in the address, so a link can open the report as someone left it.
import { computed, onMounted, reactive, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { Button, Dropdown, FormControl, Skeleton, toast } from "frappe-ui";
import { call, getList } from "@/api";
import { boot } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { formatDate, formatMoney, pickerFormat } from "@/lib/format";
import { personOptions } from "@/lib/people";
import {
	clientDefaults,
	filledFilters,
	initialFilters,
	linkRoute,
	missingRequired,
	rememberOpened,
	reportBySlug,
	rowsOf,
	sortRows,
	splitTotal,
	toCsv,
} from "@/lib/reports";
import { notLoaded } from "@/offline/reachability";
import { chosenCompanies, clientFilter, loadClients } from "@/stores/clientFilter";

const props = defineProps({ report: { type: String, required: true } });

const route = useRoute();
const router = useRouter();
const isMobile = useIsMobile();
const report = computed(() => reportBySlug(props.report));
const isFirm = boot.accountType === "CA/CS Firm";
const values = reactive(report.value ? initialFilters(report.value, route.query) : {});
const sources = reactive({});
const columns = ref([]);
const rows = ref([]);
const loading = ref(false);
const ran = ref(false);
const error = ref("");
const sortBy = ref("");
const descending = ref(false);

const shownFilters = computed(() =>
	report.value.filters.filter((filter) => !filter.firm || isFirm)
);
const missing = computed(() => missingRequired(report.value, values));
const sorted = computed(() =>
	sortBy.value ? sortRows(rows.value, sortBy.value, descending.value) : rows.value
);
const total = ref(null);

const NUMBERS = ["Int", "Float", "Currency", "Percent"];
const isNumber = (column) => NUMBERS.includes(column.fieldtype);

function cellText(column, row) {
	const value = row[column.fieldname];
	if (value == null || value === "") return "";
	switch (column.fieldtype) {
		case "Date":
			return formatDate(value);
		case "Currency":
			return formatMoney(value, row.currency || "INR");
		case "Percent":
			return `${Math.round(Number(value) * 10) / 10}%`;
		case "Check":
			return Number(value) ? "Yes" : "";
		case "Int":
		case "Float":
			return Number(value).toLocaleString("en-IN");
		default:
			return String(value);
	}
}

function optionsFor(filter) {
	const all = { label: "All", value: "" };
	if (filter.type === "select") {
		const first = report.value.defaults?.[filter.fieldname] ? [] : [all];
		return [...first, ...filter.options.map((value) => ({ label: value, value }))];
	}
	return [all, ...(sources[filter.source] || [])];
}

// The lists a report's filters choose from, read once; a list that cannot be read offers only All.
const LOADERS = {
	company: async () => boot.companies.map((name) => ({ label: name, value: name })),
	client: async () =>
		(await call("kxcompliance.api.client_choices")).map((row) => ({
			label: row.name,
			value: row.name,
		})),
	user: async () => personOptions(await call("kxcompliance.api.people_options")),
	itemType: async () => names("Compliance Item Type"),
	branch: async () => names("Branch"),
	brand: async () => names("Brand"),
};
async function names(doctype) {
	const list = await getList(doctype, { fields: ["name"], orderBy: "name asc", limit: 500 });
	return list.rows.map((row) => ({ label: row.name, value: row.name }));
}
async function loadSources() {
	const needed = new Set(shownFilters.value.map((filter) => filter.source).filter(Boolean));
	await Promise.all(
		[...needed].map(async (source) => {
			try {
				sources[source] = await LOADERS[source]();
			} catch {
				sources[source] = [];
			}
		})
	);
}

// Only the latest run is shown, so a slow answer for filters already changed cannot replace it.
let latest = 0;
async function run() {
	router.replace({ query: filledFilters(values) });
	if (missing.value.length) return;
	const ticket = ++latest;
	loading.value = true;
	error.value = "";
	try {
		const answer = await call("frappe.desk.query_report.run", {
			report_name: report.value.name,
			filters: JSON.stringify(filledFilters(values)),
		});
		if (ticket !== latest) return;
		columns.value = (answer.columns || []).filter((column) => typeof column === "object");
		const split = splitTotal(rowsOf(answer.result, columns.value), report.value.totals);
		rows.value = split.rows;
		total.value = split.total;
		ran.value = true;
	} catch (err) {
		if (ticket === latest) error.value = err.isNetwork ? notLoaded("the report") : err.message;
	} finally {
		if (ticket === latest) loading.value = false;
	}
}

function sortOn(fieldname) {
	descending.value = sortBy.value === fieldname ? !descending.value : false;
	sortBy.value = fieldname;
}

function downloadCsv() {
	const blob = new Blob([toCsv(columns.value, sorted.value)], { type: "text/csv" });
	const link = document.createElement("a");
	link.href = URL.createObjectURL(blob);
	link.download = `${report.value.title}.csv`;
	link.click();
	URL.revokeObjectURL(link.href);
}

// Excel comes from the Desk's own export, so the file is the one the Desk would give.
function downloadExcel() {
	const form = document.createElement("form");
	form.method = "POST";
	form.action = "/api/method/frappe.desk.query_report.export_query";
	const fields = {
		report_name: report.value.name,
		file_format_type: "Excel",
		filters: JSON.stringify(filledFilters(values)),
		ignore_visible_idx: "1",
		csrf_token: window.csrf_token || "",
	};
	for (const [name, value] of Object.entries(fields)) {
		const input = document.createElement("input");
		input.type = "hidden";
		input.name = name;
		input.value = value;
		form.appendChild(input);
	}
	document.body.appendChild(form);
	form.submit();
	form.remove();
	toast.info("Your download is on its way");
}

const downloads = [
	{ label: "Excel", icon: "lucide-sheet", onClick: downloadExcel },
	{ label: "CSV", icon: "lucide-file-text", onClick: downloadCsv },
];

let typing;
watch(values, () => {
	clearTimeout(typing);
	typing = setTimeout(run, 300);
});

onMounted(async () => {
	if (!report.value) return;
	rememberOpened(report.value.slug);
	loadSources();
	// With one client chosen, the report starts on it (stores/clientFilter).
	await loadClients();
	Object.assign(
		values,
		clientDefaults(report.value, route.query, {
			client: clientFilter.client,
			companies: chosenCompanies.value,
		})
	);
	run();
});
</script>
