<template>
	<AppPageHeader :title="title" :parent="parent">
		<template #actions><slot name="actions" /></template>
	</AppPageHeader>

	<div
		class="mx-auto flex w-full flex-col gap-4 px-4 py-6 sm:px-6"
		:class="layout === 'list' && !columns.length ? 'max-w-4xl' : 'max-w-7xl'"
	>
		<!-- A line on what the list is for, on lists people open rarely (Settings). -->
		<p v-if="$slots.intro" class="max-w-3xl text-base text-ink-gray-6">
			<slot name="intro" />
		</p>
		<ClientPicker v-if="byClient" />

		<!-- One line: the list's tabs and pinned views, then search, filter, sort, whose, how it
		is shown and the saved views. The tabs scroll sideways rather than push the rest down. -->
		<div class="flex flex-col gap-2 md:flex-row md:items-center">
			<div class="flex min-w-0 items-center gap-2 overflow-x-auto md:flex-1">
				<!-- On a phone, more than three tabs would run off the edge: they become a list. -->
				<FormControl
					v-if="isMobile && tabs.length > 3"
					type="select"
					class="w-full"
					:model-value="activeSaved ? '' : view"
					:options="
						activeSaved ? [{ label: activeSaved.label, value: '' }, ...tabs] : tabs
					"
					aria-label="Show"
					data-tour="list-tabs"
					@update:model-value="(value) => value && chooseTab(value)"
				/>
				<TabButtons
					v-else
					:model-value="activeSaved ? '' : view"
					:options="tabs"
					data-tour="list-tabs"
					@update:model-value="chooseTab"
				/>
				<Button
					v-for="saved in pinnedViews"
					:key="saved.name"
					size="sm"
					:variant="activeSaved?.name === saved.name ? 'subtle' : 'ghost'"
					icon-left="lucide-pin"
					:label="saved.label"
					@click="openView(saved)"
				/>
			</div>
			<div
				class="flex flex-wrap items-center gap-2 md:shrink-0 md:flex-nowrap md:justify-end"
			>
				<TextInput
					data-tour="list-search"
					v-model="search"
					type="search"
					:placeholder="t(current.searchPlaceholder || searchPlaceholder)"
					class="min-w-0 flex-1 md:w-56 md:flex-none"
					:aria-label="t(current.searchPlaceholder || searchPlaceholder)"
				>
					<template #prefix
						><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true"
					/></template>
				</TextInput>
				<!-- On a phone the filter, sort and columns fold behind one button. -->
				<Button
					v-if="isMobile"
					icon="lucide-list-filter"
					:variant="userFilters.length || showFilters ? 'subtle' : 'outline'"
					:label="
						userFilters.length
							? `${t('Filters')} · ${userFilters.length}`
							: t('Filters')
					"
					:aria-expanded="showFilters"
					@click="showFilters = !showFilters"
				/>
				<!-- One set of controls: in the line on a computer; on a phone, a row of its own
				below, shown with Filters. -->
				<ListControls
					v-show="!isMobile || showFilters"
					class="order-last basis-full md:order-none md:basis-auto"
					:key="`${listKey}:${controlsKey}`"
					:doctype="currentDoctype"
					:state="controlsState"
					:table="layout === 'table'"
					:quick-target="isMobile ? null : '#list-quick-filters'"
					@change="controlsChanged"
				/>
				<Button
					v-if="filterBy.mine"
					:variant="mine ? 'subtle' : 'ghost'"
					icon="lucide-user-round"
					:label="t('Only mine')"
					:title="t('Only mine')"
					:aria-pressed="mine"
					@click="toggleMine"
				/>
				<Dropdown :options="layoutOptions" align="end">
					<Button
						:icon="layoutOf(layout).icon"
						:label="
							layout === 'kanban'
								? boardOf(board)?.label || 'Kanban'
								: layoutOf(layout).label
						"
						:title="
							layout === 'kanban'
								? boardOf(board)?.label || 'Kanban'
								: layoutOf(layout).label
						"
						data-tour="list-layout"
					/>
				</Dropdown>
				<Dropdown :options="viewMenu" align="end">
					<Button
						v-bind="
							activeSaved
								? { iconLeft: 'lucide-bookmark', label: activeSaved.label }
								: { icon: 'lucide-bookmark', label: t('Views') }
						"
						:title="activeSaved ? activeSaved.label : t('Views')"
						:variant="activeSaved ? 'subtle' : 'ghost'"
						data-tour="list-views"
					/>
				</Dropdown>
			</div>
		</div>
		<!-- The quick filters someone chose, on their own row; hidden while there are none. -->
		<div
			v-if="!isMobile"
			id="list-quick-filters"
			class="flex flex-wrap items-center gap-2 [&:not(:has(*))]:hidden"
		/>
		<div v-if="changed" class="flex justify-end">
			<Button
				size="sm"
				variant="solid"
				icon-left="lucide-save"
				:label="activeSaved && mayChange(activeSaved) ? 'Save view' : 'Save as a view'"
				data-tour="list-save-view"
				@click="activeSaved && mayChange(activeSaved) ? updateActive() : askSave()"
			/>
		</div>

		<p
			v-if="pinned"
			class="flex items-center justify-between gap-3 rounded-lg bg-surface-gray-2 px-3 py-2 text-base text-ink-gray-8"
		>
			<span>{{ t("Showing {0}", route.query.label || t("a filtered list")) }}</span>
			<Button variant="ghost" :label="t('Show all')" @click="unpin" />
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
			v-else-if="!records.length && layout !== 'kanban'"
			class="flex flex-col items-center gap-2 py-16 text-center"
		>
			<span
				class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-6"
			>
				<span class="lucide-file-search size-6" aria-hidden="true" />
			</span>
			<p class="text-lg font-medium text-ink-gray-8">
				{{ narrowed ? t("Nothing matches the filters") : t(emptyState.title) }}
			</p>
			<p class="max-w-sm text-base text-ink-gray-5">
				{{
					narrowed
						? t("Clear a filter, or look under another tab.")
						: t(emptyState.detail)
				}}
			</p>
			<Button
				v-if="!narrowed && emptyState.action"
				class="mt-2"
				variant="solid"
				:label="t(emptyState.action.label)"
				:route="emptyState.action.route"
			/>
		</div>

		<KanbanBoard
			v-else-if="layout === 'kanban' && boardOf(board)"
			:board="boardOf(board)"
			:cards="rows"
			@move="moveCard"
		/>

		<DataTable
			v-else-if="layout === 'table' && tableColumns.length"
			:columns="tableColumns"
			:rows="rows"
		/>

		<RowList
			v-else
			:groups="groups"
			:columns="columns"
			:date-label="dateLabel"
			:name-label="nameLabel"
		/>
		<ListPager
			v-if="layout !== 'kanban' && (records.length || page > 1)"
			v-model:page="page"
			v-model:size="pageSize"
			:total="total"
			:loading="loading"
		/>
		<p v-else-if="layout === 'kanban' && records.length" class="text-base text-ink-gray-6">
			{{ rangeLine(1, records.length, records.length, t) }}
		</p>
	</div>
</template>

<script setup>
// A list of records with its own tabs, three layouts (List, Table and Kanban) and views people
// save. A view may list its own doctype by carrying doctype, fields, toRow, searchField and
// searchPlaceholder, and companyField when its company is not in "company" (for the client
// filter). The list, or each view, may also give `columns` (the List layout's extra columns on a
// computer), `dateLabel`, `boards` (Kanban boards, from lib/boards.js), `filterBy.mine` (the field
// "Only mine" narrows) and `group` (Overdue / Next 30 days / Later). Filters, sort and the
// Table's columns are Frappe's own list controls (ListControls).
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
	Button,
	Dropdown,
	FormControl,
	Skeleton,
	TabButtons,
	TextInput,
	dialog,
	toast,
} from "frappe-ui";
import { call, getList, updateDoc } from "@/api";
import { boot, isManager } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import ClientPicker from "@/components/ClientPicker.vue";
import DataTable from "@/components/DataTable.vue";
import KanbanBoard from "@/components/KanbanBoard.vue";
import ListControls from "@/components/ListControls.vue";
import ListPager from "@/components/ListPager.vue";
import RowList from "@/components/RowList.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { learnNames, nameOf } from "@/composables/usePeople";
import { BOARDS, moveAction } from "@/lib/boards";
import { companyFilters } from "@/lib/clientFilter";
import { searchFilter } from "@/lib/items";
import { parseListFilters } from "@/lib/listFilters";
import { t } from "@/lib/i18n";
import { clampPage, rangeLine, savePageSize, savedPageSize } from "@/lib/paging";
import { choiceFilters, groupBy, groupRows } from "@/lib/listViews";
import {
	LAYOUTS,
	loadViews,
	readLast,
	removeView,
	saveView,
	viewRecord,
	viewState,
	writeLast,
} from "@/lib/savedViews";
import { PERSON_FIELDS } from "@/lib/table";
import { watchDoctype } from "@/socket";
import { chosenCompanies, loadClients } from "@/stores/clientFilter";
import { notLoaded } from "@/offline/reachability";

const props = defineProps({
	title: { type: String, required: true },
	// Which list this is, for the views people save of it and its state on this device.
	listKey: { type: String, required: true },
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
	// [{ label, field, person?, value? }]: the List layout's columns on a computer, after the name.
	columns: { type: Array, default: () => [] },
	// null for a list without dates.
	dateLabel: { type: String, default: "Date" },
	nameLabel: { type: String, default: "Name" },
	// Keys of lib/boards.js BOARDS this list offers as Kanban.
	boards: { type: Array, default: () => [] },
	filterBy: { type: Object, default: () => ({}) },
});

// A board shows every card at once, up to this many.
const BOARD_LIMIT = 300;

const route = useRoute();
const router = useRouter();
const isMobile = useIsMobile();
const showFilters = ref(false);

const view = ref(
	props.views.some((option) => option.value === route.query.view)
		? route.query.view
		: props.views[0].value
);
const current = computed(() => props.views.find((option) => option.value === view.value));
const currentDoctype = computed(() => current.value.doctype || props.doctype);
// Views and the device's last state are kept per list, and per record type for lists whose tabs
// show different ones (Legal).
const listKey = computed(() =>
	current.value.doctype ? `${props.listKey}-${current.value.value}` : props.listKey
);
const columns = computed(() => current.value.columns || props.columns);
// A list without dates passes null; "" keeps the column without a heading.
const dateLabel = computed(() =>
	current.value.dateLabel !== undefined ? current.value.dateLabel : props.dateLabel
);
const nameLabel = computed(() => current.value.nameLabel || props.nameLabel);
const filterBy = computed(() => current.value.filterBy || props.filterBy);
const boardKeys = computed(() => current.value.boards || props.boards);
const boardOf = (key) => (boardKeys.value.includes(key) ? BOARDS[key] : null);
const layoutOf = (value) => LAYOUTS.find((option) => option.value === value) || LAYOUTS[0];

const search = ref(typeof route.query.q === "string" ? route.query.q : "");
const mine = ref(route.query.mine === "1");

// What the person has set up: the layout, the board, and the controls' snapshot.
const last = readLast(listKey.value);
const layout = ref(
	last?.layout === "kanban" && !boardKeys.value.length ? "list" : last?.layout || "list"
);
const board = ref(
	last?.board && boardKeys.value.includes(last.board) ? last.board : boardKeys.value[0] || ""
);
const controlsState = ref(last?.snapshot || null);
const controlsKey = ref(0);
const snapshot = ref(null);
const userFilters = ref([]);
const userOrder = ref("");
const tableColumns = ref([]);

const savedViews = ref([]);
const activeSaved = ref(null);
const pinnedViews = computed(() => savedViews.value.filter((saved) => saved.is_pinned));
const mayChange = (saved) => saved.owner === boot.user || (saved.is_shared && isManager());

const records = ref([]);
// Which page of the list is shown, how many a page holds (remembered per list on this device),
// and how many records the list has with its filters and search, counted by the server.
const page = ref(1);
const pageSize = ref(savedPageSize(listKey.value));
const total = ref(0);
const loading = ref(false);
const error = ref("");
const counts = ref({});

// A list opened from an Overview number shows exactly what it counted, until "Show all".
const pinned = computed(() => parseListFilters(route.query.f));
const narrowed = computed(() => userFilters.value.length > 0 || mine.value);
const emptyState = computed(() => props.empty(view.value, Boolean(search.value.trim())));

const tabs = computed(() =>
	props.views.map(({ label, value }) => ({
		label: counts.value[value] === undefined ? t(label) : `${t(label)} ${counts.value[value]}`,
		value,
	}))
);

const layoutOptions = computed(() => [
	...LAYOUTS.filter((option) => option.value !== "kanban").map((option) => ({
		label: option.label,
		icon: option.icon,
		onClick: () => chooseLayout(option.value),
	})),
	...boardKeys.value.map((key) => ({
		label: `Kanban: ${BOARDS[key].label.toLowerCase()}`,
		icon: "lucide-square-kanban",
		onClick: () => chooseLayout("kanban", key),
	})),
]);

// What the view is now, against the saved view it came from (or the list's plain state).
const currentState = () => ({
	layout: layout.value,
	board: board.value,
	baseView: view.value,
	snapshot: snapshot.value,
});
const changed = computed(() => {
	if (!snapshot.value) return false;
	if (!activeSaved.value)
		return narrowed.value || userOrder.value !== "" || layout.value !== "list";
	const saved = viewState(activeSaved.value);
	return (
		saved.layout !== layout.value ||
		(layout.value === "kanban" && saved.board !== board.value) ||
		JSON.stringify(saved.snapshot.filters || []) !== JSON.stringify(snapshot.value.filters) ||
		JSON.stringify(saved.snapshot.sort || []) !== JSON.stringify(snapshot.value.sort) ||
		(layout.value === "table" &&
			JSON.stringify(saved.snapshot.columns || []) !==
				JSON.stringify(snapshot.value.columns))
	);
});

const viewMenu = computed(() => {
	const own = savedViews.value.filter((saved) => saved.owner === boot.user && !saved.is_shared);
	const shared = savedViews.value.filter((saved) => saved.is_shared);
	const group = (label, items) =>
		items.length
			? [
					{
						group: label,
						options: items.map((saved) => ({
							label: saved.label,
							icon: saved.is_pinned ? "lucide-pin" : "lucide-bookmark",
							onClick: () => openView(saved),
						})),
					},
			  ]
			: [];
	const actions = [{ label: "Save as a new view", icon: "lucide-plus", onClick: askSave }];
	if (activeSaved.value && mayChange(activeSaved.value)) {
		actions.push({ label: "Rename this view", icon: "lucide-pencil", onClick: askRename });
		if (isManager()) {
			actions.push({
				label: activeSaved.value.is_pinned ? "Unpin for everyone" : "Pin for everyone",
				icon: "lucide-pin",
				onClick: togglePin,
			});
		}
		actions.push({ label: "Delete this view", icon: "lucide-trash-2", onClick: askDelete });
	}
	if (activeSaved.value) {
		actions.push({
			label: "Back to the list",
			icon: "lucide-undo-2",
			onClick: () => chooseTab(view.value),
		});
	}
	return [
		...group("Shared", shared),
		...group("Mine", own),
		{ group: "View", options: actions },
	];
});

function remember() {
	const query = {
		...route.query,
		view: view.value,
		q: search.value.trim() || undefined,
		mine: mine.value ? "1" : undefined,
	};
	if (view.value === props.views[0].value) delete query.view;
	router.replace({ query });
}

function rememberOnDevice() {
	writeLast(listKey.value, {
		layout: layout.value,
		board: board.value,
		snapshot: snapshot.value,
	});
}

// The clients are known before the first load, so a client chosen earlier applies to it.
const clientsReady = loadClients();
let reported = false;

async function controlsChanged({ snapshot: state, filters, orderBy, columns: shown }) {
	snapshot.value = state;
	const before = JSON.stringify([userFilters.value, userOrder.value]);
	userFilters.value = filters;
	userOrder.value = orderBy;
	tableColumns.value = shown;
	rememberOnDevice();
	if (!reported) {
		reported = true;
		await clientsReady;
		reloadAll();
	} else if (JSON.stringify([filters, orderBy]) !== before) reloadAll();
	else if (layout.value === "table") load();
}

function chooseTab(value) {
	activeSaved.value = null;
	if (value === view.value) {
		controlsState.value = { filters: [], sort: [] };
		controlsKey.value += 1;
		return;
	}
	view.value = value;
}

function chooseLayout(value, key) {
	layout.value = value;
	if (key) board.value = key;
	rememberOnDevice();
	load();
}

function openView(saved) {
	const state = viewState(saved);
	activeSaved.value = saved;
	if (state.baseView && props.views.some((option) => option.value === state.baseView)) {
		view.value = state.baseView;
	}
	layout.value =
		state.layout === "kanban" && !boardKeys.value.includes(state.board)
			? "list"
			: state.layout;
	board.value = state.board || board.value;
	controlsState.value = state.snapshot;
	controlsKey.value += 1;
}

function toggleMine() {
	mine.value = !mine.value;
	remember();
	reloadAll();
}

function askSave() {
	const fields = [{ name: "label", label: "Name", required: true }];
	if (isManager()) {
		fields.push({ name: "shared", label: "Share with everyone", type: "checkbox" });
		fields.push({ name: "pinned", label: "Pin as a tab for everyone", type: "checkbox" });
	}
	dialog.prompt({
		title: "Save as a view",
		message: "It keeps the tab, filters, sort, layout and, for a table, its columns.",
		confirmLabel: "Save",
		fields,
		onConfirm: async ({ values }) => {
			try {
				const saved = await saveView(
					viewRecord({
						...currentState(),
						label: values.label,
						listKey: listKey.value,
						shared: values.shared || values.pinned,
						pinned: values.pinned,
					})
				);
				await loadSaved();
				activeSaved.value =
					savedViews.value.find((entry) => entry.name === saved.name) || null;
				toast.success(`Saved "${saved.label}"`);
			} catch (err) {
				toast.error(err.message);
			}
		},
	});
}

async function updateActive() {
	const saved = activeSaved.value;
	try {
		await saveView(
			viewRecord({
				...currentState(),
				label: saved.label,
				listKey: listKey.value,
				shared: saved.is_shared,
				pinned: saved.is_pinned,
			}),
			saved.name
		);
		await loadSaved();
		activeSaved.value = savedViews.value.find((entry) => entry.name === saved.name) || null;
		toast.success(`Saved "${saved.label}"`);
	} catch (err) {
		toast.error(err.message);
	}
}

function askRename() {
	const saved = activeSaved.value;
	dialog.prompt({
		title: "Rename the view",
		confirmLabel: "Rename",
		fields: [{ name: "label", label: "Name", required: true, defaultValue: saved.label }],
		onConfirm: async ({ values }) => {
			try {
				await updateDoc("Compliance List View", saved.name, { label: values.label });
				await loadSaved();
				activeSaved.value =
					savedViews.value.find((entry) => entry.name === saved.name) || null;
			} catch (err) {
				toast.error(err.message);
			}
		},
	});
}

async function togglePin() {
	const saved = activeSaved.value;
	try {
		await updateDoc("Compliance List View", saved.name, {
			is_pinned: saved.is_pinned ? 0 : 1,
			is_shared: 1,
		});
		await loadSaved();
		activeSaved.value = savedViews.value.find((entry) => entry.name === saved.name) || null;
	} catch (err) {
		toast.error(err.message);
	}
}

function askDelete() {
	const saved = activeSaved.value;
	dialog.confirm({
		title: "Delete the view",
		message: `Delete "${saved.label}"${
			saved.is_shared ? " for everyone it is shared with" : ""
		}? The records are not touched.`,
		confirmLabel: "Delete",
		theme: "red",
		onConfirm: async () => {
			try {
				await removeView(saved.name);
				activeSaved.value = null;
				await loadSaved();
			} catch (err) {
				toast.error(err.message);
			}
		},
	});
}

async function moveCard({ card, from, to, undo }) {
	const target = boardOf(board.value);
	const action = moveAction(target, from, to);
	if (action === "none") return undo();
	if (action === "open") {
		undo();
		toast.info(`${card.title}: fill in the filing details to move it on.`);
		router.push(card.to);
		return;
	}
	try {
		const doctype = currentDoctype.value;
		await updateDoc(doctype, card.record.name, { [target.field]: to });
		toast.success(`${card.title} moved`);
		reloadAll();
	} catch (err) {
		undo();
		toast.error(err.message);
	}
}

const unpin = () => {
	const query = { ...route.query };
	delete query.f;
	delete query.label;
	router.replace({ query }).then(() => reloadAll());
};

function filtersOf(option) {
	return [
		...(option.filters || []),
		...(props.byClient ? companyFilters(chosenCompanies.value, option.companyField) : []),
		...choiceFilters(
			{ mine: mine.value },
			{ mineField: (option.filterBy || props.filterBy).mine, user: boot.user }
		),
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
		record,
	}))
);
// In the view's own order the rows fall under when they are due, or under what `group` returns
// for each record (with `groupOrder` for the headings); another sort lists them.
const groups = computed(() => {
	const { group, groupOrder } = current.value;
	if (!group || userOrder.value || pinned.value) {
		return [{ key: "all", label: "", rows: rows.value }];
	}
	return typeof group === "function"
		? groupBy(rows.value, (row) => group(row.record), groupOrder || [])
		: groupRows(rows.value);
});

function fieldsToLoad() {
	const base = current.value.fields || props.fields;
	const extra = [
		...(layout.value === "table" ? tableColumns.value.map((column) => column.fieldname) : []),
		...(layout.value === "kanban" && boardOf(board.value) ? [boardOf(board.value).field] : []),
	];
	return [...new Set([...base, ...extra.filter((field) => /^[a-z_]+$/.test(field))])];
}

// Each load takes a ticket; only the latest one's answer is shown, so a slow answer for a
// tab or search the person has already left cannot replace the rows they are looking at.
let latest = 0;

async function load() {
	const ticket = ++latest;
	loading.value = true;
	error.value = "";
	const kanban = layout.value === "kanban" && boardOf(board.value);
	try {
		const { orderBy, searchField } = current.value;
		// A board has its own scope in place of the tab's: every record it has columns for.
		const scope = kanban?.scope ? kanban.scope(new Date()) : null;
		const narrowing = [
			...filtersOf({ ...current.value, filters: [] }),
			...userFilters.value,
			...searchFilter(search.value, searchField || props.searchField),
		];
		const query = (filters, limit) =>
			getList(currentDoctype.value, {
				fields: fieldsToLoad(),
				filters,
				orderBy: userOrder.value || orderBy,
				start: kanban ? 0 : (page.value - 1) * pageSize.value,
				limit,
			});
		let loaded;
		let counted = null;
		if (scope) {
			const [main, also] = await Promise.all([
				query([...scope.filters, ...narrowing], BOARD_LIMIT),
				scope.also ? query([...scope.also, ...narrowing], BOARD_LIMIT) : { rows: [] },
			]);
			loaded = { rows: [...main.rows, ...also.rows] };
		} else {
			const filters = [
				...(pinned.value || [...filtersOf(current.value), ...userFilters.value]),
				...searchFilter(search.value, searchField || props.searchField),
			];
			const [rowsOfPage, count] = await Promise.all([
				query(filters, kanban ? BOARD_LIMIT : pageSize.value),
				kanban ? null : countOf(currentDoctype.value, filters),
			]);
			loaded = rowsOfPage;
			counted = count;
		}
		// A slower, earlier load must not overwrite the rows or the count of a later one.
		if (ticket !== latest) return;
		if (counted !== null) total.value = counted;
		const people = [
			...columns.value.filter((column) => column.person).map((column) => column.field),
			...(layout.value === "table" ? PERSON_FIELDS : []),
		];
		await learnNames(
			loaded.rows.flatMap((row) => people.map((field) => row[field])).filter(Boolean)
		);
		records.value = loaded.rows;
		// Past the last page (records removed since): go to the last one there is.
		if (!kanban && !loaded.rows.length && page.value > 1) {
			page.value = clampPage(page.value, total.value, pageSize.value);
		}
	} catch (err) {
		if (ticket === latest) error.value = err.isNetwork ? notLoaded("this list") : err.message;
	} finally {
		if (ticket === latest) loading.value = false;
	}
}

// How many records match, counted by the server with the same permissions as the list.
const countOf = (doctype, filters) => call("frappe.client.get_count", { doctype, filters });

// How many each tab holds with the filters chosen (not the search), counted by the server.
async function loadCounts() {
	const entries = await Promise.all(
		props.views.map(async (option) => {
			// Another record type's filters do not apply to its tab.
			const same = (option.doctype || props.doctype) === currentDoctype.value;
			try {
				const count = await countOf(option.doctype || props.doctype, [
					...filtersOf(option),
					...(same ? userFilters.value : []),
				]);
				return [option.value, count];
			} catch {
				// A tab without its number still works.
				return [option.value, undefined];
			}
		})
	);
	counts.value = Object.fromEntries(entries);
}

async function loadSaved() {
	try {
		savedViews.value = await loadViews(listKey.value, boot.user);
	} catch {
		// Without saved views the list itself still works.
		savedViews.value = [];
	}
}

// A new tab, filter or choice starts from the first page; someone else's change keeps the page.
function reloadAll({ keepPage = false } = {}) {
	if (!keepPage) records.value = [];
	loadCounts();
	firstPageOr(keepPage);
}

// Back to the first page, which the page watcher loads; or, already there, load it here.
function firstPageOr(keepPage = false) {
	if (!keepPage && page.value !== 1) page.value = 1;
	else load();
}

let typing;
watch(view, (now, before) => {
	records.value = [];
	const query = { ...route.query };
	delete query.f;
	delete query.label;
	const otherType =
		(props.views.find((option) => option.value === before)?.doctype || props.doctype) !==
		currentDoctype.value;
	if (otherType) {
		// Another record type: its own views and its own last state.
		const state = readLast(listKey.value);
		layout.value =
			state?.layout === "kanban" && !boardKeys.value.length
				? "list"
				: state?.layout || "list";
		board.value = boardKeys.value.includes(state?.board)
			? state.board
			: boardKeys.value[0] || "";
		controlsState.value = state?.snapshot || null;
		controlsKey.value += 1;
		loadSaved();
	}
	router.replace({ query }).then(() => {
		remember();
		reloadAll();
	});
});
watch(chosenCompanies, () => {
	if (!props.byClient) return;
	reloadAll();
});
watch(search, () => {
	clearTimeout(typing);
	typing = setTimeout(() => {
		remember();
		firstPageOr();
	}, 300);
});
// Another page, or another page size (remembered for this list), is read from the server.
watch([page, pageSize], () => load());
watch(pageSize, (size) => savePageSize(listKey.value, size));
watch(listKey, (key) => {
	pageSize.value = savedPageSize(key);
});

// Someone else's change to a record of this type reloads the list and its counts.
let stopWatching = null;
function watchCurrent() {
	stopWatching?.();
	stopWatching = watchDoctype(currentDoctype.value, () => reloadAll({ keepPage: true }));
}
watch(currentDoctype, watchCurrent);
onBeforeUnmount(() => stopWatching?.());

// The rows load once the controls report their filters (and the clients are known).
onMounted(() => {
	loadSaved();
	watchCurrent();
});
</script>
