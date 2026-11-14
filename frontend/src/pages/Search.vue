<template>
	<AppPageHeader title="Search" />

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6 sm:px-6">
		<div ref="box">
			<TextInput
				v-model="text"
				type="search"
				size="md"
				placeholder="Name, number or reference"
				aria-label="Search the register, filings, cases and trademarks"
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
		<p v-else-if="text.trim().length < MIN_LENGTH" class="text-base text-ink-gray-5">
			Search register items, filings, cases and trademarks by name, number or reference, such
			as a licence number, an acknowledgement number or a case number.
		</p>
		<div
			v-else-if="searching && !sections.length"
			class="flex flex-col gap-3"
			aria-busy="true"
		>
			<Skeleton v-for="index in 4" :key="index" class="h-10 w-full rounded-lg" />
		</div>
		<div
			v-else-if="!sections.length"
			class="flex flex-col items-center gap-2 py-12 text-center"
		>
			<span
				class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-6"
			>
				<span class="lucide-search-x size-6" aria-hidden="true" />
			</span>
			<p class="text-lg font-medium text-ink-gray-8">Nothing matches “{{ text.trim() }}”</p>
			<p class="max-w-sm text-base text-ink-gray-5">Try part of a name or number.</p>
		</div>

		<section
			v-for="section in sections"
			:key="section.key"
			class="flex flex-col gap-1"
			:aria-labelledby="`search-${section.key}`"
		>
			<h2
				:id="`search-${section.key}`"
				class="px-3 pb-1 text-sm font-medium text-ink-gray-6"
			>
				{{ section.label }}
			</h2>
			<WorkRow v-for="row in section.rows" :key="row.key" :row="row" />
		</section>
	</div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Skeleton, TextInput } from "frappe-ui";
import { call } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import WorkRow from "@/components/WorkRow.vue";
import { MIN_LENGTH, resultSections } from "@/lib/search";
import { notLoaded } from "@/offline/reachability";

const route = useRoute();
const router = useRouter();

// The search lives in the address (?q=), so going back from a result returns to it.
const text = ref(String(route.query.q || ""));
const results = ref(null);
const searching = ref(false);
const error = ref("");
const box = ref(null);

const sections = computed(() => resultSections(results.value));

let typing;
let latest = 0;
async function run() {
	const query = text.value.trim();
	const ticket = ++latest;
	error.value = "";
	if (query.length < MIN_LENGTH) {
		results.value = null;
		return;
	}
	searching.value = true;
	try {
		const found = await call("compliance_plus.api.search", { text: query });
		// A slower earlier search must not replace the answer to a later one.
		if (ticket === latest) results.value = found;
	} catch (err) {
		if (ticket === latest)
			error.value = err.isNetwork ? notLoaded("this search") : err.message;
	} finally {
		if (ticket === latest) searching.value = false;
	}
}

watch(text, (value) => {
	router.replace({ query: value.trim() ? { q: value.trim() } : {} });
	clearTimeout(typing);
	typing = setTimeout(run, 250);
});

onMounted(async () => {
	run();
	await nextTick();
	box.value?.querySelector("input")?.focus();
});
</script>
