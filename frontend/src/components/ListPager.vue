<template>
	<nav
		ref="bar"
		class="flex flex-col gap-3 border-t border-outline-gray-1 pt-3 sm:flex-row sm:items-center sm:justify-between"
		:aria-label="t('Pages')"
	>
		<div class="flex items-center gap-3">
			<p class="whitespace-nowrap text-base text-ink-gray-6" aria-live="polite">
				{{ rangeLine(page, size, total, t) }}
			</p>
			<FormControl
				v-if="total > PAGE_SIZES[0]"
				class="w-20"
				type="select"
				size="sm"
				:aria-label="t('Per page')"
				:model-value="String(size)"
				:options="
					PAGE_SIZES.map((option) => ({ label: String(option), value: String(option) }))
				"
				@update:model-value="chooseSize"
			/>
		</div>

		<div v-if="count > 1" class="flex items-center gap-1 self-end sm:self-auto">
			<Button
				variant="ghost"
				icon="lucide-chevron-left"
				:aria-label="t('Previous page')"
				:disabled="page <= 1 || loading"
				@click="go(page - 1)"
			/>
			<!-- A phone has room for where it is; a computer gets the page numbers. -->
			<span class="px-2 text-base text-ink-gray-7 sm:hidden">{{ page }} / {{ count }}</span>
			<template v-for="(number, index) in numbers" :key="number ?? `gap-${index}`">
				<span
					v-if="number === null"
					class="hidden px-1 text-base text-ink-gray-5 sm:inline"
					aria-hidden="true"
					>…</span
				>
				<Button
					v-else
					class="hidden min-w-8 sm:inline-flex"
					:variant="number === page ? 'subtle' : 'ghost'"
					:label="String(number)"
					:aria-label="t('Page {0}', number)"
					:aria-current="number === page ? 'page' : undefined"
					:disabled="loading"
					@click="go(number)"
				/>
			</template>
			<Button
				variant="ghost"
				icon="lucide-chevron-right"
				:aria-label="t('Next page')"
				:disabled="page >= count || loading"
				@click="go(page + 1)"
			/>
		</div>
	</nav>
</template>

<script setup>
// The foot of a list: how many records there are and which are shown, how many a page holds
// (20, 50 or 100), and the way to the other pages.
import { computed, nextTick, ref } from "vue";
import { Button, FormControl } from "frappe-ui";
import { t } from "@/lib/i18n";
import { PAGE_SIZES, pageCount, pageNumbers, rangeLine } from "@/lib/paging";

const props = defineProps({
	total: { type: Number, default: 0 },
	loading: { type: Boolean, default: false },
});
const page = defineModel("page", { type: Number, default: 1 });
const size = defineModel("size", { type: Number, default: PAGE_SIZES[0] });

const count = computed(() => pageCount(props.total, size.value));
const numbers = computed(() => pageNumbers(page.value, count.value));

const bar = ref(null);

// The next page starts at its top: the list's scrolling area (or the window) goes back up.
function backToTop() {
	nextTick(() => {
		let area = bar.value?.parentElement;
		while (
			area &&
			!(
				area.scrollHeight > area.clientHeight &&
				/auto|scroll/.test(getComputedStyle(area).overflowY)
			)
		) {
			area = area.parentElement;
		}
		(area || window).scrollTo({ top: 0 });
	});
}

function go(number) {
	page.value = Math.min(Math.max(1, number), count.value);
	backToTop();
}

// A new size starts from the page holding the first row now shown, so the place is kept.
function chooseSize(value) {
	// The new size is used as chosen: the model reads the old one until the list takes it.
	const chosen = Number(value);
	const first = (page.value - 1) * size.value;
	size.value = chosen;
	page.value = Math.floor(first / chosen) + 1;
	backToTop();
}
</script>
