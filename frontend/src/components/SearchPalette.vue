<template>
	<Teleport to="body">
		<div
			v-if="paletteOpen"
			class="fixed inset-0 z-50 flex items-start justify-center px-4 pt-[12vh]"
			@keydown.esc.prevent="close"
		>
			<div class="absolute inset-0 bg-black/30" aria-hidden="true" @click="close" />
			<div
				class="relative flex max-h-[70vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl bg-surface-base shadow-2xl"
				role="dialog"
				aria-modal="true"
				aria-label="Quick search"
			>
				<div class="flex items-center gap-3 border-b border-outline-gray-1 px-4">
					<span
						class="lucide-search size-5 shrink-0 text-ink-gray-5"
						aria-hidden="true"
					/>
					<input
						ref="input"
						v-model="text"
						type="text"
						role="combobox"
						aria-autocomplete="list"
						aria-controls="quick-search-list"
						:aria-expanded="items.length > 0"
						:aria-activedescendant="
							items[active] ? `quick-${items[active].key}` : undefined
						"
						placeholder="Search, or go to a page"
						class="h-14 flex-1 border-0 bg-transparent px-0 text-lg text-ink-gray-8 placeholder:text-ink-gray-4 focus:outline-none focus:ring-0"
						@keydown.down.prevent="moveBy(1)"
						@keydown.up.prevent="moveBy(-1)"
						@keydown.enter.prevent="choose(items[active])"
					/>
					<LoadingIndicator v-if="searching" class="size-4 text-ink-gray-5" />
					<kbd
						class="hidden rounded border border-outline-gray-2 px-1.5 py-0.5 text-xs text-ink-gray-5 sm:block"
						>Esc</kbd
					>
				</div>

				<ul
					id="quick-search-list"
					role="listbox"
					class="flex flex-col overflow-y-auto p-2"
					aria-label="Results"
				>
					<template v-for="(item, index) in items" :key="item.key">
						<li
							v-if="index === 0 || items[index - 1].group !== item.group"
							role="presentation"
							class="px-2 pb-1 pt-3 text-xs font-medium text-ink-gray-5 first:pt-1"
						>
							{{ item.group }}
						</li>
						<li
							:id="`quick-${item.key}`"
							role="option"
							:aria-selected="index === active"
							class="flex cursor-pointer items-center gap-3 rounded-lg px-2 py-2"
							:class="
								index === active ? 'bg-surface-gray-3' : 'hover:bg-surface-gray-2'
							"
							@mousemove="active = index"
							@click="choose(item)"
						>
							<span
								class="flex size-7 shrink-0 items-center justify-center rounded-full"
								:class="item.tile || 'bg-surface-gray-2 text-ink-gray-6'"
							>
								<span :class="item.icon" class="size-4" aria-hidden="true" />
							</span>
							<span class="flex min-w-0 flex-1 flex-col">
								<span class="truncate text-base text-ink-gray-8">{{
									item.label
								}}</span>
								<span
									v-if="item.detail"
									class="truncate text-sm text-ink-gray-5"
									>{{ item.detail }}</span
								>
							</span>
							<span v-if="item.status" class="shrink-0 text-sm text-ink-gray-5">{{
								item.status
							}}</span>
							<span
								v-if="index === active"
								class="lucide-corner-down-left size-4 shrink-0 text-ink-gray-5"
								aria-hidden="true"
							/>
						</li>
					</template>
					<li
						v-if="!items.length"
						role="presentation"
						class="px-2 py-8 text-center text-base text-ink-gray-5"
					>
						{{ searching ? "Searching…" : `Nothing matches “${text.trim()}”.` }}
					</li>
				</ul>

				<div
					class="flex items-center gap-4 border-t border-outline-gray-1 px-4 py-2 text-xs text-ink-gray-5"
				>
					<span>↑ ↓ to move</span>
					<span>Enter to open</span>
					<span class="ml-auto">{{ shortcut }} opens this anywhere</span>
				</div>
			</div>
		</div>
	</Teleport>
</template>

<script setup>
// Quick search: Ctrl/⌘ K (App.vue) or the side bar's Search opens it over any page. It jumps to pages and
// actions, and finds records as the full Search does, a few of each kind; "See all results"
// opens the Search page with the same words. The arrow keys move, Enter opens.
import { computed, nextTick, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { LoadingIndicator } from "frappe-ui";
import { call } from "@/api";
import { checksOnly } from "@/boot";
import { kindTint } from "@/lib/areas";
import {
	goToItems,
	matchItems,
	paletteOpen,
	recentSearches,
	rememberSearch,
	shortcutLabel,
} from "@/lib/quickSearch";
import { MIN_LENGTH, resultSections } from "@/lib/search";
import { KINDS } from "@/pages/myWork";

// How many records of each kind the box shows, and of pages and actions.
const PER_KIND = 3;
const PAGES = 6;

const router = useRouter();
const shortcut = shortcutLabel();
const text = ref("");
const results = ref(null);
const searching = ref(false);
const active = ref(0);
const input = ref(null);
const everywhere = goToItems();

const query = computed(() => text.value.trim());

const items = computed(() => {
	if (query.value.length < MIN_LENGTH) {
		const recent = recentSearches().map((entry) => ({
			key: `recent-${entry}`,
			group: "Recent searches",
			label: entry,
			icon: "lucide-history",
			fill: entry,
		}));
		return [...recent, ...matchItems(everywhere, query.value).slice(0, 10)];
	}
	const pages = matchItems(everywhere, query.value).slice(0, PAGES);
	const records = resultSections(results.value).flatMap((section) =>
		section.rows.slice(0, PER_KIND).map((row) => ({
			key: `${section.key}-${row.key}`,
			group: section.label,
			label: row.title,
			detail: row.detail,
			status: row.status,
			icon: KINDS[row.kind]?.icon || "lucide-file",
			tile: kindTint(row.kind).tile,
			to: row.to,
			record: true,
		}))
	);
	return [
		...pages,
		...records,
		{
			key: "all-results",
			group: "Search",
			label: `See all results for “${query.value}”`,
			icon: "lucide-search",
			to: { name: "Search", query: { q: query.value } },
			record: true,
		},
	];
});

function moveBy(step) {
	if (!items.value.length) return;
	active.value = (active.value + step + items.value.length) % items.value.length;
}

function close() {
	paletteOpen.value = false;
}

function choose(item) {
	if (!item) return;
	if (item.fill) {
		text.value = item.fill;
		return;
	}
	if (item.record) rememberSearch(query.value);
	close();
	if (item.to) router.push(item.to);
}

let typing;
let latest = 0;
async function run() {
	const ticket = ++latest;
	if (query.value.length < MIN_LENGTH) {
		results.value = null;
		searching.value = false;
		return;
	}
	// Someone who only checks licences has no records to search, only their pages.
	if (checksOnly()) return;
	searching.value = true;
	try {
		const found = await call("kxcompliance.api.search", { text: query.value });
		if (ticket === latest) results.value = found;
	} catch {
		// The pages and "See all results" still work; the Search page says what went wrong.
		if (ticket === latest) results.value = null;
	} finally {
		if (ticket === latest) searching.value = false;
	}
}

watch(text, () => {
	active.value = 0;
	clearTimeout(typing);
	typing = setTimeout(run, 200);
});
watch(items, () => {
	if (active.value >= items.value.length) active.value = 0;
});
watch(paletteOpen, async (open) => {
	if (!open) return;
	text.value = "";
	results.value = null;
	active.value = 0;
	await nextTick();
	input.value?.focus();
});
</script>
