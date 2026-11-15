<template>
	<AppPageHeader :title="title" :parent="parent">
		<template #actions><slot name="actions" /></template>
	</AppPageHeader>

	<div
		class="mx-auto flex w-full flex-col gap-4 px-4 py-6 sm:px-6"
		:class="layout === 'list' && !columns.length ? 'max-w-4xl' : 'max-w-7xl'"
	>
		<ClientPicker v-if="byClient" />

		<!-- The list's own tabs and the views pinned for everyone, and search. -->
		<div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
			<div class="flex min-w-0 items-center gap-2 overflow-x-auto">
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
			<TextInput
				data-tour="list-search"
				v-model="search"
				type="search"
				:placeholder="t(current.searchPlaceholder || searchPlaceholder)"
				class="w-full shrink-0 md:w-64"
				:aria-label="t(current.searchPlaceholder || searchPlaceholder)"
			>
				<template #prefix
					><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true"
				/></template>
			</TextInput>
		</div>

		<!-- Filters on the left; how the list is shown and the saved views on the right. -->
		<div class="flex flex-wrap items-start justify-between gap-2">
			<div class="flex min-w-0 flex-1 flex-wrap items-center gap-2">
				<!-- On a phone the filters fold behind one button, so the rows show first. -->
				<Button
					v-if="isMobile"
					size="sm"
					icon-left="lucide-list-filter"
					:variant="userFilters.length ? 'subtle' : 'outline'"
					:label="
						userFilters.length
							? `${t('Filters')} · ${userFilters.length}`
							: t('Filters')
					"
					:aria-expanded="showFilters"
					@click="showFilters = !showFilters"
				/>
				<div v-show="!isMobile || showFilters" class="w-full sm:w-auto">
					<ListControls
						:key="`${listKey}:${controlsKey}`"
						:doctype="currentDoctype"
						:state="controlsState"
						:table="layout === 'table'"
						@change="controlsChanged"
					/>
				</div>
				<Button
					v-if="filterBy.mine"
					size="sm"
					:variant="mine ? 'subtle' : 'ghost'"
					icon-left="lucide-user-round"
					:label="t('Only mine')"
					:aria-pressed="mine"
					@click="toggleMine"
				/>
				<Button
					v-if="changed"
					size="sm"
					variant="solid"
					icon-left="lucide-save"
					:label="activeSaved && mayChange(activeSaved) ? 'Save view' : 'Save as a view'"
					data-tour="list-save-view"
					@click="activeSaved && mayChange(activeSaved) ? updateActive() : askSave()"
				/>
			</div>
			<div class="flex items-center gap-2">
				<Dropdown :options="layoutOptions" align="end">
					<Button
						:icon-left="layoutOf(layout).icon"
						:label="
							layout === 'kanban'
								? boardOf(board)?.label || 'Kanban'
								: layoutOf(layout).label
						"
						data-tour="list-layout"
					/>
				</Dropdown>
				<Dropdown :options="viewMenu" align="end">
					<Button
						icon-left="lucide-bookmark"
						:label="activeSaved ? activeSaved.label : t('Views')"
						:variant="activeSaved ? 'subtle' : 'outline'"
						data-tour="list-views"
					/>
				</Dropdown>
			</div>
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

		<div v-else class="flex flex-col" data-tour="list-rows">
			<div
				class="hidden items-center gap-3 border-b border-outline-gray-1 px-3 pb-2 text-xs font-medium text-ink-gray-5 sm:flex"
				aria-hidden="true"
			>
				<span class="w-8 shrink-0" />
				<span class="flex-1">{{ t("Name") }}</span>
				<span v-for="column in columns" :key="column.label" class="w-40 shrink-0">{{
					t(column.label)
				}}</span>
				<span class="w-36 shrink-0">{{ t("Status") }}</span>
				<span class="w-28 shrink-0 text-right">{{ t(dateLabel) }}</span>
			</div>
			<template v-for="group in groups" :key="group.key">
				<h2
					v-if="group.label"
					class="flex items-center gap-2 px-3 pb-1 pt-4 text-sm font-semibold"
					:class="group.key === 'overdue' ? 'text-ink-red-4' : 'text-ink-gray-7'"
				>
					{{ t(group.label) }}
					<span class="font-normal text-ink-gray-5">{{ group.rows.length }}</span>
				</h2>
				<div class="flex flex-col [&>*+*]:border-t [&>*+*]:border-outline-gray-1">
					<WorkRow
						v-for="entry in group.rows"
						:key="entry.key"
						:row="entry"
						:cells="entry.cells"
					/>
				</div>
			</template>
		</div>
		<Button
			v-if="hasMore && layout !== 'kanban'"
			class="self-center"
			:label="t('Show more')"
			:loading="loading"
			@click="load(true)"
		/>
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
import WorkRow from "@/components/WorkRow.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { learnNames, nameOf } from "@/composables/usePeople";
import { BOARDS, moveAction } from "@/lib/boards";
import { companyFilters } from "@/lib/clientFilter";
import { searchFilter } from "@/lib/items";
import { parseListFilters } from "@/lib/listFilters";
import { t } from "@/lib/i18n";
import { choiceFilters, groupRows } from "@/lib/listViews";
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
	dateLabel: { type: String, default: "Date" },
	// Keys of lib/boards.js BOARDS this list offers as Kanban.
	boards: { type: Array, default: () => [] },
	filterBy: { type: Object, default: () => ({}) },
});

const PAGE = 30;
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
const dateLabel = computed(() => current.value.dateLabel || props.dateLabel);
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
const hasMore = ref(false);
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
	router.replace({ query }).then(() => load());
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
// In the view's own date order the rows fall under when they are due; another sort lists them.
const groups = computed(() =>
	current.value.group && !userOrder.value && !pinned.value
		? groupRows(rows.value)
		: [{ key: "all", label: "", rows: rows.value }]
);

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

async function load(more = false) {
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
				start: more ? records.value.length : 0,
				limit,
			});
		let page;
		if (scope) {
			const [main, also] = await Promise.all([
				query([...scope.filters, ...narrowing], BOARD_LIMIT),
				scope.also ? query([...scope.also, ...narrowing], BOARD_LIMIT) : { rows: [] },
			]);
			page = { rows: [...main.rows, ...also.rows], hasMore: false };
		} else {
			page = await query(
				[
					...(pinned.value || [...filtersOf(current.value), ...userFilters.value]),
					...searchFilter(search.value, searchField || props.searchField),
				],
				kanban ? BOARD_LIMIT : PAGE
			);
		}
		if (ticket !== latest) return;
		const people = [
			...columns.value.filter((column) => column.person).map((column) => column.field),
			...(layout.value === "table" ? PERSON_FIELDS : []),
		];
		await learnNames(
			page.rows.flatMap((row) => people.map((field) => row[field])).filter(Boolean)
		);
		records.value = more ? [...records.value, ...page.rows] : page.rows;
		hasMore.value = !kanban && page.hasMore;
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
			// Another record type's filters do not apply to its tab.
			const same = (option.doctype || props.doctype) === currentDoctype.value;
			try {
				const count = await call("frappe.client.get_count", {
					doctype: option.doctype || props.doctype,
					filters: [...filtersOf(option), ...(same ? userFilters.value : [])],
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

async function loadSaved() {
	try {
		savedViews.value = await loadViews(listKey.value, boot.user);
	} catch {
		// Without saved views the list itself still works.
		savedViews.value = [];
	}
}

function reloadAll() {
	records.value = [];
	load();
	loadCounts();
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
		load();
	}, 300);
});
// Someone else's change to a record of this type reloads the list and its counts.
let stopWatching = null;
function watchCurrent() {
	stopWatching?.();
	stopWatching = watchDoctype(currentDoctype.value, reloadAll);
}
watch(currentDoctype, watchCurrent);
onBeforeUnmount(() => stopWatching?.());

// The rows load once the controls report their filters (and the clients are known).
onMounted(() => {
	loadSaved();
	watchCurrent();
});
</script>
