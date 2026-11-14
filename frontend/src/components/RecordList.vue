<template>
	<AppPageHeader :title="title">
		<template #actions><slot name="actions" /></template>
	</AppPageHeader>

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-5 px-4 py-6 sm:px-6">
		<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
			<TabButtons v-model="view" :options="tabs" />
			<TextInput
				v-model="search"
				type="search"
				:placeholder="current.searchPlaceholder || searchPlaceholder"
				class="sm:w-64"
				:aria-label="current.searchPlaceholder || searchPlaceholder"
			>
				<template #prefix
					><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true"
				/></template>
			</TextInput>
		</div>

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
			<p class="text-lg font-medium text-ink-gray-8">{{ emptyState.title }}</p>
			<p class="max-w-sm text-base text-ink-gray-5">{{ emptyState.detail }}</p>
		</div>

		<div v-else class="flex flex-col gap-1">
			<WorkRow
				v-for="record in records"
				:key="record.name"
				:row="(current.toRow || toRow)(record)"
			/>
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
// list its own doctype by carrying doctype, fields, toRow, searchField and searchPlaceholder.
import { computed, onMounted, ref, watch } from "vue";
import { Button, Skeleton, TabButtons, TextInput } from "frappe-ui";
import { getList } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import WorkRow from "@/components/WorkRow.vue";
import { searchFilter } from "@/lib/items";
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
	// (view, searching) => { title, detail }
	empty: { type: Function, required: true },
});

const PAGE = 30;

const view = ref(props.views[0].value);
const search = ref("");
const records = ref([]);
const hasMore = ref(false);
const loading = ref(false);
const error = ref("");

const current = computed(() => props.views.find((option) => option.value === view.value));
const tabs = computed(() => props.views.map(({ label, value }) => ({ label, value })));
const emptyState = computed(() => props.empty(view.value, Boolean(search.value.trim())));

async function load(more = false) {
	loading.value = true;
	error.value = "";
	try {
		const { doctype, fields, filters, orderBy, searchField } = current.value;
		const page = await getList(doctype || props.doctype, {
			fields: fields || props.fields,
			filters: [...filters, ...searchFilter(search.value, searchField || props.searchField)],
			orderBy,
			start: more ? records.value.length : 0,
			limit: PAGE,
		});
		records.value = more ? [...records.value, ...page.rows] : page.rows;
		hasMore.value = page.hasMore;
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this list") : err.message;
	} finally {
		loading.value = false;
	}
}

let typing;
watch(view, () => {
	records.value = [];
	load();
});
watch(search, () => {
	clearTimeout(typing);
	typing = setTimeout(() => load(), 300);
});
onMounted(() => load());
</script>
