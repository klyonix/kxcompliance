<template>
	<AppPageHeader
		:title="title || fallbackTitle"
		:parent="{
			label: 'Legal',
			route: { name: 'Legal', query: { view: doctype === 'Trademark' ? 'marks' : 'cases' } },
		}"
	>
		<template #actions>
			<Dropdown v-if="loaded && menu.length" :options="menu" align="end">
				<Button variant="ghost" icon="lucide-ellipsis" label="More actions" />
			</Dropdown>
		</template>
	</AppPageHeader>

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-6 sm:px-6">
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>

		<div v-else-if="!loaded" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton class="h-6 w-1/2 rounded" />
			<Skeleton class="h-4 w-1/3 rounded" />
			<Skeleton class="mt-4 h-48 w-full rounded-lg" />
		</div>

		<template v-else>
			<section class="flex flex-col gap-2">
				<div class="flex flex-wrap items-center gap-2">
					<Badge :label="status" :theme="theme" size="md" />
					<span
						class="text-base"
						:class="due.late ? 'font-medium text-ink-red-4' : 'text-ink-gray-6'"
					>
						{{ due.text }}
					</span>
				</div>
				<p v-if="subtitle" class="text-base text-ink-gray-6">{{ subtitle }}</p>
			</section>

			<slot />

			<LegalDates
				:doctype="doctype"
				:name="name"
				:may-act="mayAct"
				@changed="$emit('changed')"
			/>

			<section class="flex flex-col gap-3" aria-labelledby="details-heading">
				<h2 id="details-heading" class="text-base font-semibold text-ink-gray-8">
					Details
				</h2>
				<dl class="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
					<div
						v-for="fact in shownFacts"
						:key="fact.label"
						class="flex flex-col gap-0.5"
					>
						<dt class="text-sm text-ink-gray-5">{{ fact.label }}</dt>
						<dd class="text-base text-ink-gray-8">{{ fact.value }}</dd>
					</div>
				</dl>
				<div v-for="note in shownNotes" :key="note.label" class="flex flex-col gap-0.5">
					<span class="text-sm text-ink-gray-5">{{ note.label }}</span>
					<p class="whitespace-pre-line text-base text-ink-gray-8">{{ note.value }}</p>
				</div>
			</section>

			<section
				v-if="documents.length"
				class="flex flex-col gap-3"
				aria-labelledby="documents-heading"
			>
				<h2 id="documents-heading" class="text-base font-semibold text-ink-gray-8">
					Documents
				</h2>
				<a
					v-for="document in documents"
					:key="document.name"
					:href="document.file_url"
					target="_blank"
					class="flex items-center gap-3 rounded-lg px-1 py-1.5 hover:bg-surface-gray-2"
				>
					<span class="lucide-file-text size-4 text-ink-gray-5" aria-hidden="true" />
					<span class="truncate text-base text-ink-gray-8">{{
						document.file_name
					}}</span>
				</a>
			</section>
		</template>
	</div>
</template>

<script setup>
// The page of one case or trademark: where it stands, its dates, its details and documents.
import { computed, onMounted, ref, watch } from "vue";
import { Badge, Button, Dropdown, Skeleton } from "frappe-ui";
import { call } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import LegalDates from "@/components/LegalDates.vue";
import { deskActions } from "@/navigation";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, required: true },
	loaded: { type: Boolean, default: false },
	error: { type: String, default: "" },
	title: { type: String, default: "" },
	fallbackTitle: { type: String, default: "" },
	status: { type: String, default: "" },
	theme: { type: String, default: "gray" },
	due: { type: Object, default: () => ({ text: "", late: false }) },
	subtitle: { type: String, default: "" },
	// [[label, value]]; empty values are left out
	facts: { type: Array, default: () => [] },
	notes: { type: Array, default: () => [] },
	mayAct: { type: Boolean, default: false },
});
defineEmits(["changed"]);

const documents = ref([]);

const keep = (pairs) =>
	pairs.filter(([, value]) => value).map(([label, value]) => ({ label, value }));
const shownFacts = computed(() => keep(props.facts));
const shownNotes = computed(() => keep(props.notes));

const menu = computed(() => deskActions(props.doctype, props.name));

async function loadDocuments() {
	try {
		documents.value = await call("compliance_plus.api.documents", {
			doctype: props.doctype,
			name: props.name,
		});
	} catch {
		// Documents are extra; the page is still useful without them, offline included.
		documents.value = [];
	}
}

watch(() => props.name, loadDocuments);
onMounted(loadDocuments);
</script>
