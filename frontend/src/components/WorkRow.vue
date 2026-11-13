<template>
	<component
		:is="row.to ? RouterLink : 'a'"
		:to="row.to"
		:href="row.to ? undefined : row.href"
		class="group flex items-center gap-3 rounded-lg px-3 py-2.5 hover:bg-surface-gray-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4"
	>
		<span
			class="flex size-8 shrink-0 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-6"
		>
			<span :class="kind.icon" class="size-4" aria-hidden="true" />
			<span class="sr-only">{{ kind.label }}</span>
		</span>
		<span class="flex min-w-0 flex-1 flex-col gap-0.5">
			<span class="truncate text-base font-medium text-ink-gray-8">{{ row.title }}</span>
			<span class="truncate text-sm text-ink-gray-5">
				<!-- Phones have no room for the badge, so the status leads the detail line. -->
				<span class="sm:hidden" :class="STATUS_TEXT[row.theme] || STATUS_TEXT.gray">{{
					row.status
				}}</span
				><span class="sm:hidden" aria-hidden="true"> · </span>{{ row.detail }}
			</span>
		</span>
		<span class="hidden w-40 shrink-0 justify-end sm:flex">
			<Badge :label="row.status" :theme="row.theme" />
		</span>
		<span
			class="w-24 shrink-0 text-right text-sm"
			:class="row.due.late ? 'font-medium text-ink-red-4' : 'text-ink-gray-6'"
		>
			{{ row.due.text }}
		</span>
	</component>
</template>

<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { Badge } from "frappe-ui";
import { KINDS } from "@/pages/myWork";

const props = defineProps({ row: { type: Object, required: true } });
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
