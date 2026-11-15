<template>
	<AppPageHeader :title="title" :parent="parent">
		<template #actions><slot name="actions" /></template>
	</AppPageHeader>

	<div
		class="mx-auto flex w-full flex-col gap-4 px-4 py-6 sm:px-6"
		:class="columns.length ? 'max-w-6xl' : 'max-w-4xl'"
	>
		<ClientPicker v-if="byClient" />
		<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
			<TabButtons v-model="view" :options="tabs" data-tour="list-tabs" />
			<div class="flex items-center gap-2">
				<TextInput
					data-tour="list-search"
					v-model="search"
					type="search"
					:placeholder="current.searchPlaceholder || searchPlaceholder"
					class="min-w-0 flex-1 sm:w-64 sm:flex-none"
					:aria-label="current.searchPlaceholder || searchPlaceholder"
				>
					<template #prefix
						><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true"
					/></template>
				</TextInput>
				<Button
					v-if="offersChoices"
					:label="chosenCount ? `Filter · ${chosenCount}` : 'Filter'"
					icon-left="lucide-list-filter"
					:variant="chosenCount ? 'subtle' : 'outline'"
					:aria-expanded="showChoices"
					data-tour="list-filter"
					@click="showChoices = !showChoices"
				/>
			</div>
		</div>

		<div
			v-if="offersChoices && showChoices"
			class="grid grid-cols-1 gap-3 rounded-lg bg-surface-gray-1 p-3 sm:grid-cols-4"
		>
			<FormControl
				v-if="filterBy.company && companyOptions.length > 2"
				type="select"
				label="Company"
				:model-value="choices.company || ''"
				:options="companyOptions"
				@update:model-value="choose('company', $event)"
			/>
			<FormControl
				v-if="filterBy.type"
				type="select"
				:label="filterBy.type.label"
				:model-value="choices.type || ''"
				:options="typeOptions"
				@update:model-value="choose('type', $event)"
			/>
			<FormControl
				v-if="sorts.length"
				type="select"
				label="Sort by"
				:model-value="choices.sort || sorts[0].value"
				:options="sorts.map(({ label, value }) => ({ label, value }))"
				@update:model-value="choose('sort', $event === sorts[0].value ? '' : $event)"
			/>
			<div v-if="filterBy.mine" class="flex items-end pb-1.5">
				<FormControl
					type="checkbox"
					label="Only mine"
					:model-value="Boolean(choices.mine)"
					@update:model-value="choose('mine', $event)"
				/>
			</div>
		</div>

		<p
			v-if="pinned"
			class="flex items-center justify-between gap-3 rounded-lg bg-surface-gray-2 px-3 py-2 text-base text-ink-gray-8"
		>
			<span>Showing {{ route.query.label || "a filtered list" }}</span>
			<Button variant="ghost" label="Show all" @click="unpin" />
		</p>

		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>

		<div v-else-if="loading && !records.length" class="flex flex-col gap-4" aria-busy="true">
			<div v-for="index in 6" :key="index" class="flex items-center gap-3 px-3">
				<Skeleton class="size-8 rounded-full" />
				<div class="flex flex-1 flex-col gap-1.5">
					<Skeleton class="h-4 w-2/3 rounded" />
					<Skeleton class="h-3 w-1/3 rounded" />
				</div>
				<Skeleton class="h-3 w-16 rounded" />
			</div>
		</div>

		<div
			v-else-if="!records.length"
			class="flex flex-col items-center gap-2 py-16 text-center"
		>
			<span
				class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-6"
			>
				<span class="lucide-file-search size-6" aria-hidden="true" />
			</span>
			<p class="text-lg font-medium text-ink-gray-8">
				{{ chosenCount ? "Nothing matches the filters" : emptyState.title }}
			</p>
			<p class="max-w-sm text-base text-ink-gray-5">
				{{
					chosenCount ? "Clear a filter, or look under another tab." : emptyState.detail
				}}
			</p>
			<Button v-if="chosenCount" class="mt-2" label="Clear filters" @click="clearChoices" />
			<Button
				v-else-if="emptyState.action"
				class="mt-2"
				variant="solid"
				:label="emptyState.action.label"
				:route="emptyState.action.route"
			/>
		</div>

		<div v-else class="flex flex-col" data-tour="list-rows">
			<div
				class="hidden items-center gap-3 border-b border-outline-gray-1 px-3 pb-2 text-xs font-medium text-ink-gray-5 sm:flex"
				aria-hidden="true"
			>
				<span class="w-8 shrink-0" />
				<span class="flex-1">Name</span>
				<span v-for="column in columns" :key="column.label" class="w-40 shrink-0">{{
					column.label
				}}</span>
				<span class="w-36 shrink-0">Status</span>
				<span class="w-28 shrink-0 text-right">{{ dateLabel }}</span>
			</div>
			<template v-for="group in groups" :key="group.key">
				<h2
					v-if="group.label"
					class="flex items-center gap-2 px-3 pb-1 pt-4 text-sm font-semibold"
					:class="group.key === 'overdue' ? 'text-ink-red-4' : 'text-ink-gray-7'"
				>
					{{ group.label }}
					<span class="font-normal text-ink-gray-5">{{ group.rows.length }}</span>
				</h2>
				<WorkRow
					v-for="entry in group.rows"
					:key="entry.key"
					:row="entry"
					:cells="entry.cells"
				/>
			</template>
			<Button
				v-if="hasMore"
				class="mt-3 self-center"
				label="Show more"
				:loading="loading"
				@click="load(true)"
			/>
		</div>
	</div>
</template>

<script setup>
// A searchable list with a few fixed views, as the Register, Filings and Legal show. A view may
// list its own doctype by carrying doctype, fields, toRow, searchField and searchPlaceholder, and
// companyField when its company is not in "company" (for the client filter). The list, or each
// view, may also give `columns` (extra columns on a computer), `dateLabel` (the heading of the
// date column), `sorts`, `filterBy` ({ company, type: { field, label, load }, mine: field }) and
// `group` (Overdue / Next 30 days / Later, for views in date order).
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button, FormControl, Skeleton, TabButtons, TextInput } from "frappe-ui";
import { call, getList } from "@/api";
import { boot } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import ClientPicker from "@/components/ClientPicker.vue";
import WorkRow from "@/components/WorkRow.vue";
import { learnNames, nameOf } from "@/composables/usePeople";
import { companyFilters } from "@/lib/clientFilter";
import { searchFilter } from "@/lib/items";
import { parseListFilters } from "@/lib/listFilters";
import { choiceCount, choiceFilters, groupRows, orderFor, readListChoices } from "@/lib/listViews";
import { chosenCompanies, loadClients } from "@/stores/clientFilter";
import { notLoaded } from "@/offline/reachability";

const props = defineProps({
	title: { type: String, required: true },
	doctype: { type: String, default: "" },
	fields: { type: Array, default: () => [] },
	// [{ label, value, filters, orderBy }]
	views: { type: Array, required: true },
	toRow: { type: Function, default: null },
	searchField: { type: String, default: "title" },
	searchPlaceholder: { type: String, default: "Search by title" },
	// (view, searching) => { title, detail, action?: { label, route } }: the action is the next step.
	empty: { type: Function, required: true },
	// For a list that belongs under another page, as AppPageHeader takes it.
	parent: { type: Object, default: null },
	// False for records that belong to no company, which the client filter cannot narrow.
	byClient: { type: Boolean, default: true },
	// [{ label, field, person?, value? }]: shown on a computer, after the name; `value(record)`
	// works a cell out, `person` shows a user's name.
	columns: { type: Array, default: () => [] },
	dateLabel: { type: String, default: "Date" },
	// [{ label, value, orderBy }]; the first is the view's own order.
	sorts: { type: Array, default: () => [] },
	filterBy: { type: Object, default: () => ({}) },
});

const PAGE = 30;

// The tab, search, filters and sort live in the address, so Back from a record returns to them.
const route = useRoute();
const router = useRouter();
const view = ref(
	props.views.some((option) => option.value === route.query.view)
		? route.query.view
		: props.views[0].value
);
const search = ref(typeof route.query.q === "string" ? route.query.q : "");
const current = computed(() => props.views.find((option) => option.value === view.value));
const columns = computed(() => current.value.columns || props.columns);
const dateLabel = computed(() => current.value.dateLabel || props.dateLabel);
const sorts = computed(() => current.value.sorts || props.sorts);
const filterBy = computed(() => current.value.filterBy || props.filterBy);

const types = ref([]);
const choices = reactive(
	readListChoices(route.query, {
		sorts: sorts.value,
		companies: boot.companies,
		// Checked again once the types are known.
		types: null,
	})
);
const chosenCount = computed(() => choiceCount(choices));
const showChoices = ref(chosenCount.value > 0);
const offersChoices = computed(
	() =>
		sorts.value.length > 1 ||
		filterBy.value.type ||
		filterBy.value.mine ||
		(filterBy.value.company && boot.companies.length > 1)
);
const companyOptions = computed(() => [
	{ label: "Every company", value: "" },
	...boot.companies.map((company) => ({ label: company, value: company })),
]);
const typeOptions = computed(() => [
	{ label: "Every type", value: "" },
	...types.value.map((type) => ({ label: type, value: type })),
]);

function remember() {
	const query = {
		...route.query,
		view: view.value,
		q: search.value.trim() || undefined,
		sort: choices.sort || undefined,
		company: choices.company || undefined,
		type: choices.type || undefined,
		mine: choices.mine ? "1" : undefined,
	};
	if (view.value === props.views[0].value) delete query.view;
	router.replace({ query });
}

function choose(key, value) {
	if (value) choices[key] = value;
	else delete choices[key];
	remember();
	records.value = [];
	load();
	loadCounts();
}

function clearChoices() {
	for (const key of ["company", "type", "mine"]) delete choices[key];
	remember();
	load();
	loadCounts();
}

const records = ref([]);
const hasMore = ref(false);
const loading = ref(false);
const error = ref("");
const counts = ref({});

// A list opened from an Overview number shows exactly what it counted, until "Show all".
const pinned = computed(() => parseListFilters(route.query.f));
function unpin() {
	const query = { ...route.query };
	delete query.f;
	delete query.label;
	router.replace({ query }).then(() => load());
}
const tabs = computed(() =>
	props.views.map(({ label, value }) => ({
		label: counts.value[value] === undefined ? label : `${label} ${counts.value[value]}`,
		value,
	}))
);
const emptyState = computed(() => props.empty(view.value, Boolean(search.value.trim())));

function filtersOf(option) {
	const by = option.filterBy || props.filterBy;
	return [
		...(option.filters || []),
		...(props.byClient ? companyFilters(chosenCompanies.value, option.companyField) : []),
		...choiceFilters(choices, {
			companyField: option.companyField || "company",
			typeField: by.type?.field,
			mineField: by.mine,
			user: boot.user,
		}),
	];
}

const cellsOf = (record) =>
	columns.value.map((column) => {
		if (column.value) return column.value(record);
		return column.person ? nameOf(record[column.field]) : record[column.field] || "";
	});

const rows = computed(() =>
	records.value.map((record) => ({
		...(current.value.toRow || props.toRow)(record),
		cells: cellsOf(record),
	}))
);
// In the view's own date order the rows fall under when they are due; another sort lists them.
const groups = computed(() =>
	current.value.group && !choices.sort && !pinned.value
		? groupRows(rows.value)
		: [{ key: "all", label: "", rows: rows.value }]
);

// Each load takes a ticket; only the latest one's answer is shown, so a slow answer for a
// tab or search the person has already left cannot replace the rows they are looking at.
let latest = 0;

async function load(more = false) {
	const ticket = ++latest;
	loading.value = true;
	error.value = "";
	try {
		const { doctype, fields, orderBy, searchField } = current.value;
		const page = await getList(doctype || props.doctype, {
			fields: fields || props.fields,
			filters: [
				...(pinned.value || filtersOf(current.value)),
				...searchFilter(search.value, searchField || props.searchField),
			],
			orderBy: orderFor(choices, sorts.value, orderBy),
			start: more ? records.value.length : 0,
			limit: PAGE,
		});
		if (ticket !== latest) return;
		const people = columns.value.filter((column) => column.person);
		if (people.length) {
			await learnNames(
				page.rows.flatMap((row) => people.map((column) => row[column.field]))
			);
		}
		records.value = more ? [...records.value, ...page.rows] : page.rows;
		hasMore.value = page.hasMore;
	} catch (err) {
		if (ticket === latest) error.value = err.isNetwork ? notLoaded("this list") : err.message;
	} finally {
		if (ticket === latest) loading.value = false;
	}
}

// How many each tab holds with the filters chosen (not the search), counted by the server.
async function loadCounts() {
	const entries = await Promise.all(
		props.views.map(async (option) => {
			try {
				const count = await call("frappe.client.get_count", {
					doctype: option.doctype || props.doctype,
					filters: filtersOf(option),
				});
				return [option.value, count];
			} catch {
				// A tab without its number still works.
				return [option.value, undefined];
			}
		})
	);
	counts.value = Object.fromEntries(entries);
}

async function loadTypes() {
	const by = filterBy.value.type;
	if (!by?.load) return;
	try {
		types.value = await by.load();
		if (choices.type && !types.value.includes(choices.type)) delete choices.type;
	} catch {
		types.value = [];
	}
}

let typing;
watch(view, () => {
	records.value = [];
	const query = { ...route.query };
	delete query.f;
	delete query.label;
	router.replace({ query }).then(() => {
		remember();
		load();
		loadTypes();
	});
});
watch(chosenCompanies, () => {
	if (!props.byClient) return;
	records.value = [];
	load();
	loadCounts();
});
watch(search, () => {
	clearTimeout(typing);
	typing = setTimeout(() => {
		remember();
		load();
	}, 300);
});
// A client chosen earlier on this device applies once the clients are known.
onMounted(() =>
	loadClients().then(() => {
		load();
		loadCounts();
		loadTypes();
	})
);
</script>
