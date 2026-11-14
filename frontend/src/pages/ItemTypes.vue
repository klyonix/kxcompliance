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

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-6 sm:px-6">
		<p class="text-base text-ink-gray-6">
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
			<Skeleton v-for="index in 5" :key="index" class="h-12 w-full rounded-lg" />
		</div>
		<ul v-else class="flex flex-col">
			<li v-for="type in types" :key="type.name">
				<RouterLink
					:to="{ name: 'ItemType', params: { name: type.name } }"
					class="flex items-center gap-3 rounded-lg px-3 py-2.5 hover:bg-surface-gray-2"
				>
					<span class="flex min-w-0 flex-1 flex-col">
						<span
							class="truncate text-base font-medium"
							:class="type.is_active ? 'text-ink-gray-8' : 'text-ink-gray-5'"
							>{{ type.name }}</span
						>
						<span class="truncate text-sm text-ink-gray-5">{{
							typeSummary(type)
						}}</span>
					</span>
					<span v-if="!type.is_active" class="text-sm text-ink-gray-5">Not in use</span>
				</RouterLink>
			</li>
		</ul>
	</div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { Button, Skeleton } from "frappe-ui";
import { getList } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { typeSummary } from "@/lib/itemTypes";
import { notLoaded } from "@/offline/reachability";

const types = ref(null);
const error = ref("");

onMounted(async () => {
	try {
		types.value = (
			await getList("Compliance Item Type", {
				fields: [
					"name",
					"category",
					"renewal_cycle_months",
					"requires_document",
					"is_active",
				],
				orderBy: "name asc",
				limit: 500,
			})
		).rows;
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("the item types") : err.message;
	}
});
</script>
