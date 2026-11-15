<template>
	<RouterLink
		:to="row.to"
		class="group flex items-start gap-3 rounded-lg px-3 py-[var(--row-pad)] hover:bg-surface-gray-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4 sm:items-center"
	>
		<span
			class="flex size-8 shrink-0 items-center justify-center rounded-full"
			:class="kindTint(row.kind).tile"
		>
			<span :class="kind.icon" class="size-4" aria-hidden="true" />
			<span class="sr-only">{{ kind.label }}</span>
		</span>
		<span class="flex min-w-0 flex-1 flex-col gap-0.5">
			<!-- Phones wrap the title over two lines rather than cut it off. -->
			<span
				class="line-clamp-2 text-base font-medium text-ink-gray-8 sm:line-clamp-1 sm:truncate"
				>{{ row.title }}</span
			>
			<span class="line-clamp-1 text-sm text-ink-gray-5">{{ row.detail }}</span>
			<!-- On a phone the status and date have a line of their own. -->
			<span class="flex items-center gap-2 text-sm sm:hidden">
				<span
					class="inline-flex items-center gap-1"
					:class="STATUS_TEXT[row.theme] || STATUS_TEXT.gray"
					><span
						:class="STATUS_ICONS[row.theme] || STATUS_ICONS.gray"
						class="size-3.5"
						aria-hidden="true"
					/>{{ t(row.status) }}</span
				>
				<template v-if="row.due.text">
					<span class="text-ink-gray-4" aria-hidden="true">·</span>
					<span
						:class="row.due.late ? 'font-medium text-ink-red-4' : 'text-ink-gray-6'"
						>{{ row.due.text }}</span
					>
				</template>
			</span>
		</span>
		<span
			v-for="(cell, index) in cells"
			:key="index"
			class="hidden w-40 shrink-0 truncate text-sm text-ink-gray-6 sm:block"
			>{{ cell || "—" }}</span
		>
		<span class="hidden w-36 shrink-0 sm:flex">
			<!-- Colour and an icon, never colour alone. -->
			<Badge :label="t(row.status)" :theme="row.theme">
				<template #prefix>
					<span
						:class="STATUS_ICONS[row.theme] || STATUS_ICONS.gray"
						class="size-3"
						aria-hidden="true"
					/>
				</template>
			</Badge>
		</span>
		<span
			class="hidden w-28 shrink-0 text-right text-sm sm:block"
			:class="row.due.late ? 'font-medium text-ink-red-4' : 'text-ink-gray-6'"
		>
			{{ row.due.text }}
		</span>
	</RouterLink>
</template>

<script setup>
// One row of a list: what it is, its status and when. `cells` are a list's extra columns, shown
// on a computer under the headings RecordList draws.
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { Badge } from "frappe-ui";
import { kindTint } from "@/lib/areas";
import { STATUS_ICONS } from "@/lib/status";
import { KINDS } from "@/pages/myWork";

const props = defineProps({
	row: { type: Object, required: true },
	cells: { type: Array, default: () => [] },
});
const kind = computed(() => KINDS[props.row.kind]);
// Text colours that match each badge theme, for the phone layout.
const STATUS_TEXT = {
	red: "text-ink-red-4",
	amber: "text-ink-amber-4",
	blue: "text-ink-blue-4",
	green: "text-ink-green-4",
	gray: "text-ink-gray-6",
};
</script>
