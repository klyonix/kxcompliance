<template>
	<AppPageHeader
		title="Blocks and warnings"
		:parent="{ label: 'Licence rules', route: { name: 'LicenceRules' } }"
	/>

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-6 sm:px-6">
		<p class="text-base text-ink-gray-6">
			Sales and purchases a licence rule stopped or warned about. A manager can let a blocked
			document through once, with a reason that is kept.
		</p>
		<TabButtons v-model="view" :options="CHECK_VIEWS" data-tour="licence-blocks-tabs" />

		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<div v-else-if="!rows" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton v-for="index in 4" :key="index" class="h-14 w-full rounded-lg" />
		</div>
		<p v-else-if="!rows.length" class="py-12 text-center text-base text-ink-gray-5">
			{{ EMPTY[view] }}
		</p>
		<ul v-else class="flex flex-col" data-tour="licence-blocks-list">
			<li
				v-for="row in rows"
				:key="row.name"
				class="flex flex-col gap-2 border-b border-outline-gray-1 py-3 sm:flex-row sm:items-start"
			>
				<div class="flex min-w-0 flex-1 flex-col gap-0.5">
					<a
						:href="documentLink(row.reference_doctype, row.reference_name)"
						class="text-base font-medium text-ink-gray-8 hover:underline"
						>{{ row.reference_doctype }} {{ row.reference_name }}</a
					>
					<span class="text-sm text-ink-gray-6"
						>{{ row.party }} · {{ row.item_type }}</span
					>
					<span v-if="row.message" class="text-sm text-ink-gray-5">{{
						row.message
					}}</span>
					<span class="text-sm text-ink-gray-5">{{
						[formatDateTime(row.checked_on), nameOf(row.checked_by)]
							.filter(Boolean)
							.join(" · ")
					}}</span>
				</div>
				<Badge v-if="allowed.has(key(row))" label="Let through" theme="green" />
				<Button
					v-else-if="view === 'blocked' && isManager()"
					label="Allow this once"
					@click="allowOnce(row)"
				/>
			</li>
		</ul>
	</div>
</template>

<script setup>
// Documents a licence rule blocked or warned about, and those let through once by a manager.
import { onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Badge, Button, Skeleton, TabButtons, dialog, toast } from "frappe-ui";
import { createDoc, getList } from "@/api";
import { isManager } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { learnNames, nameOf } from "@/composables/usePeople";
import { formatDateTime } from "@/lib/format";
import { CHECK_VIEWS, documentLink, latestPerDocument, overrideKey } from "@/lib/licenceRules";
import { notLoaded } from "@/offline/reachability";

const EMPTY = {
	blocked: "Nothing has been blocked.",
	warned: "No warnings.",
	allowed: "Nothing has been let through.",
};

const route = useRoute();
const router = useRouter();
const view = ref(
	CHECK_VIEWS.some((option) => option.value === route.query.view) ? route.query.view : "blocked"
);
const rows = ref(null);
const allowed = ref(new Set());
const error = ref("");
const key = (row) => overrideKey(row.reference_doctype, row.reference_name);

async function load() {
	rows.value = null;
	error.value = "";
	const result = CHECK_VIEWS.find((option) => option.value === view.value).result;
	try {
		const logs = await getList("Licence Check Log", {
			fields: [
				"name",
				"result",
				"reference_doctype",
				"reference_name",
				"party",
				"item_type",
				"message",
				"checked_by",
				"checked_on",
			],
			filters: [["result", "=", result]],
			orderBy: "checked_on desc",
			limit: 200,
		});
		const latest = latestPerDocument(logs.rows);
		const keys = latest.map(key);
		const overrides = keys.length
			? await getList("Licence Override", {
					fields: ["override_key"],
					filters: [["override_key", "in", keys]],
					limit: keys.length,
			  })
			: { rows: [] };
		allowed.value = new Set(overrides.rows.map((row) => row.override_key));
		learnNames(latest.map((row) => row.checked_by));
		rows.value = latest;
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("the licence checks") : err.message;
	}
}

function allowOnce(row) {
	dialog.prompt({
		title: "Allow this once",
		message: `${row.reference_doctype} ${row.reference_name} for ${row.party} can then be saved and submitted without the ${row.item_type}. The reason is kept.`,
		confirmLabel: "Allow",
		fields: [{ name: "reason", label: "Why", type: "textarea", required: true }],
		onConfirm: async ({ values }) => {
			try {
				await createDoc("Licence Override", {
					reference_doctype: row.reference_doctype,
					reference_name: row.reference_name,
					reason: values.reason,
				});
				allowed.value = new Set([...allowed.value, key(row)]);
				toast.success(`${row.reference_name} can go through once`);
			} catch (err) {
				toast.error(err.message);
			}
		},
	});
}

watch(view, () => {
	router.replace({ query: { view: view.value } });
	load();
});
onMounted(load);
</script>
