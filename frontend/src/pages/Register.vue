<template>
	<AppPageHeader title="Register" />

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-5 px-4 py-6 sm:px-6">
		<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
			<TabButtons v-model="view" :options="REGISTER_VIEWS" />
			<TextInput
				v-model="search"
				type="search"
				placeholder="Search by title"
				class="sm:w-64"
				aria-label="Search the register"
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

		<div v-else-if="loading && !items.length" class="flex flex-col gap-4" aria-busy="true">
			<div v-for="index in 6" :key="index" class="flex items-center gap-3 px-3">
				<Skeleton class="size-8 rounded-full" />
				<div class="flex flex-1 flex-col gap-1.5">
					<Skeleton class="h-4 w-2/3 rounded" />
					<Skeleton class="h-3 w-1/3 rounded" />
				</div>
				<Skeleton class="h-3 w-16 rounded" />
			</div>
		</div>

		<div v-else-if="!items.length" class="flex flex-col items-center gap-2 py-16 text-center">
			<span
				class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-6"
			>
				<span class="lucide-file-search size-6" aria-hidden="true" />
			</span>
			<p class="text-lg font-medium text-ink-gray-8">{{ emptyTitle }}</p>
			<p class="max-w-sm text-base text-ink-gray-5">{{ emptyDetail }}</p>
		</div>

		<div v-else class="flex flex-col gap-1">
			<WorkRow v-for="item in items" :key="item.name" :row="itemRow(item)" />
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
import { computed, onMounted, ref, watch } from "vue";
import { Button, Skeleton, TabButtons, TextInput } from "frappe-ui";
import { getList } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import WorkRow from "@/components/WorkRow.vue";
import { ITEM_LIST_FIELDS, REGISTER_VIEWS, itemRow, searchFilter } from "@/lib/items";

const PAGE = 30;

const view = ref("attention");
const search = ref("");
const items = ref([]);
const hasMore = ref(false);
const loading = ref(false);
const error = ref("");

const emptyTitle = computed(() =>
	search.value.trim()
		? "No matches"
		: view.value === "attention"
		? "Nothing needs attention"
		: "No items yet"
);
const emptyDetail = computed(() =>
	search.value.trim()
		? "Try another word, or look under All."
		: "Licences, registrations, certificates, insurance and subscriptions appear here once they are recorded."
);

async function load(more = false) {
	loading.value = true;
	error.value = "";
	try {
		const filters = [
			...REGISTER_VIEWS.find((option) => option.value === view.value).filters,
			...searchFilter(search.value),
		];
		const page = await getList("Compliance Item", {
			fields: ITEM_LIST_FIELDS,
			filters,
			orderBy: "valid_until asc",
			start: more ? items.value.length : 0,
			limit: PAGE,
		});
		items.value = more ? [...items.value, ...page.rows] : page.rows;
		hasMore.value = page.hasMore;
	} catch (err) {
		error.value = err.isNetwork
			? "You are offline, and this list has not been loaded on this device yet."
			: err.message;
	} finally {
		loading.value = false;
	}
}

let typing;
watch(view, () => load());
watch(search, () => {
	clearTimeout(typing);
	typing = setTimeout(() => load(), 300);
});
onMounted(() => load());
</script>
