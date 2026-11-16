<template>
	<AppPageHeader
		title="Register item types"
		:parent="{ label: 'Settings', route: { name: 'Settings' } }"
	>
		<template #actions>
			<Button
				variant="solid"
				icon-left="lucide-plus"
				label="Add a type"
				:route="{ name: 'ItemTypeNew' }"
			/>
		</template>
	</AppPageHeader>

	<div class="mx-auto flex w-full max-w-6xl flex-col gap-5 px-4 py-6 sm:px-6">
		<p class="text-base text-ink-gray-5">
			A type sets how often its items renew, how long after expiry they still count, whether
			a certificate is needed, and when reminders go out.
		</p>
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<div v-else-if="!types" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton v-for="index in 5" :key="index" class="h-16 w-full rounded-lg" />
		</div>
		<template v-else>
			<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
				<TabButtons
					v-model="view"
					:options="TYPE_VIEWS"
					class="self-start overflow-x-auto"
				/>
				<TextInput
					v-model="search"
					type="search"
					placeholder="Search by name"
					aria-label="Search by name"
					class="w-full sm:w-72"
				>
					<template #prefix
						><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true"
					/></template>
				</TextInput>
			</div>
			<div v-if="!rows.length" class="flex flex-col items-center gap-2 py-16 text-center">
				<p class="text-lg font-medium text-ink-gray-8">{{ emptyText.title }}</p>
				<p class="max-w-sm text-base text-ink-gray-5">{{ emptyText.detail }}</p>
				<Button
					v-if="emptyText.action"
					variant="solid"
					class="mt-2"
					:label="emptyText.action"
					:route="{ name: 'ItemTypeNew' }"
				/>
			</div>
			<RowList
				v-else
				paged="item-types"
				:rows="rows"
				:columns="TYPE_COLUMNS"
				name-label="Type"
				:date-label="null"
			/>
		</template>
	</div>
</template>

<script setup>
// The register item types as this firm uses them: a type shared with other firms shows the
// firm's own settings where it has set them (kxcompliance.api.item_types).
import { computed, onMounted, ref } from "vue";
import { Button, Skeleton, TabButtons, TextInput } from "frappe-ui";
import { call } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import RowList from "@/components/RowList.vue";
import { TYPE_COLUMNS, TYPE_VIEWS, typeEmpty, typeRow, typesShown } from "@/lib/itemTypes";
import { notLoaded } from "@/offline/reachability";

const types = ref(null);
const error = ref("");
const view = ref("active");
const search = ref("");

const rows = computed(() => typesShown(types.value, view.value, search.value).map(typeRow));
const emptyText = computed(() => typeEmpty(view.value, Boolean(search.value.trim())));

onMounted(async () => {
	try {
		types.value = await call("kxcompliance.api.item_types");
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("the item types") : err.message;
	}
});
</script>
