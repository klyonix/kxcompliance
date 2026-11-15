<template>
	<AppPageHeader title="Search" />

	<div class="mx-auto flex w-full max-w-4xl flex-col gap-5 px-4 py-6 sm:px-6">
		<div ref="box">
			<TextInput
				v-model="text"
				type="search"
				size="md"
				placeholder="Name, number or reference"
				aria-label="Search everything"
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

		<!-- Before anything is typed: what it looks through, and the last few searches. -->
		<template v-else-if="text.trim().length < MIN_LENGTH">
			<p class="text-base text-ink-gray-5">
				Every word you type must appear somewhere, in any order: “gst pune 3b” finds the
				Pune company's GSTR-3B. It looks through the register, filings, cases, trademarks,
				clients, companies, signatories, document requests and more.
			</p>
			<section
				v-if="recent.length"
				class="flex flex-col gap-2"
				aria-labelledby="recent-heading"
			>
				<h2 id="recent-heading" class="text-sm font-medium text-ink-gray-6">
					Recent searches
				</h2>
				<div class="flex flex-wrap gap-2">
					<Button
						v-for="query in recent"
						:key="query"
						icon-left="lucide-history"
						:label="query"
						@click="text = query"
					/>
				</div>
			</section>
			<p class="hidden text-sm text-ink-gray-5 sm:block">
				Tip: press {{ shortcut }} anywhere to search without leaving the page.
			</p>
		</template>

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
			<p class="max-w-sm text-base text-ink-gray-5">
				Try fewer words, or part of a name or number.
			</p>
		</div>

		<template v-else>
			<!-- Each kind with its count; a phone chooses from a list. -->
			<FormControl
				v-if="isMobile"
				v-model="tab"
				type="select"
				:options="tabs"
				aria-label="Show"
			/>
			<TabButtons v-else v-model="tab" :options="tabs" class="self-start overflow-x-auto" />

			<section
				v-for="section in shown"
				:key="section.key"
				class="flex flex-col gap-1"
				:aria-labelledby="`search-${section.key}`"
			>
				<h2
					:id="`search-${section.key}`"
					class="flex items-center gap-2 px-3 pb-1 text-sm font-semibold text-ink-gray-7"
				>
					{{ section.label }}
					<span class="font-normal text-ink-gray-5">{{ countText(section.rows) }}</span>
				</h2>
				<div class="flex flex-col [&>*+*]:border-t [&>*+*]:border-outline-gray-1">
					<WorkRow
						v-for="row in tab === 'all'
							? section.rows.slice(0, PREVIEW)
							: section.rows"
						:key="row.key"
						:row="row"
						@click="remember"
					/>
				</div>
				<Button
					v-if="tab === 'all' && section.rows.length > PREVIEW"
					class="self-start"
					variant="ghost"
					icon-right="lucide-arrow-right"
					:label="`Show all ${countText(section.rows)}`"
					@click="tab = section.key"
				/>
				<p
					v-if="tab !== 'all' && section.rows.length >= CANDIDATES"
					class="px-3 text-sm text-ink-gray-5"
				>
					These are the closest {{ CANDIDATES }}. Add a word to narrow it down.
				</p>
			</section>
		</template>
	</div>
</template>

<script setup>
// Search everything the person may read: every word must appear, closest matches first, by kind
// with counts. The words and the kind chosen are kept in the address (?q=, ?kind=), so going back
// from a result returns to them.
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button, FormControl, Skeleton, TabButtons, TextInput } from "frappe-ui";
import { call } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import WorkRow from "@/components/WorkRow.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import {
	CANDIDATES,
	MIN_LENGTH,
	PREVIEW,
	countText,
	resultSections,
	searchTabs,
} from "@/lib/search";
import { recentSearches, rememberSearch, shortcutLabel } from "@/lib/quickSearch";
import { notLoaded } from "@/offline/reachability";

const route = useRoute();
const router = useRouter();
const isMobile = useIsMobile();
const shortcut = shortcutLabel();

const text = ref(String(route.query.q || ""));
const tab = ref(String(route.query.kind || "all"));
const results = ref(null);
const searching = ref(false);
const error = ref("");
const box = ref(null);
const recent = ref(recentSearches());

const sections = computed(() => resultSections(results.value));
const tabs = computed(() => searchTabs(sections.value));
const shown = computed(() =>
	tab.value === "all"
		? sections.value
		: sections.value.filter((section) => section.key === tab.value)
);

// Opening a result keeps the words among the recent searches.
const remember = () => rememberSearch(text.value);

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
		const found = await call("kxcompliance.api.search", { text: query });
		// A slower earlier search must not replace the answer to a later one.
		if (ticket === latest) results.value = found;
	} catch (err) {
		if (ticket === latest)
			error.value = err.isNetwork ? notLoaded("this search") : err.message;
	} finally {
		if (ticket === latest) searching.value = false;
	}
}

function keepInAddress() {
	const query = {};
	if (text.value.trim()) query.q = text.value.trim();
	if (tab.value !== "all") query.kind = tab.value;
	router.replace({ query });
}

watch(text, () => {
	tab.value = "all";
	keepInAddress();
	clearTimeout(typing);
	typing = setTimeout(run, 250);
});
watch(tab, keepInAddress);
// A kind that found nothing for these words goes back to All.
watch(sections, (now) => {
	if (!results.value) return;
	if (tab.value !== "all" && !now.some((section) => section.key === tab.value)) {
		tab.value = "all";
	}
});

onMounted(async () => {
	run();
	await nextTick();
	box.value?.querySelector("input")?.focus();
});
</script>
