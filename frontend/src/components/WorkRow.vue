<template>
	<div
		class="group flex flex-col rounded-lg hover:bg-surface-gray-2 sm:flex-row sm:items-center"
	>
		<component
			:is="row.to ? RouterLink : row.href ? 'a' : 'div'"
			:to="row.to"
			:href="row.href"
			class="flex min-w-0 flex-1 items-start gap-3 rounded-lg px-3 py-[var(--row-pad)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4 sm:items-center"
		>
			<Avatar
				v-if="row.avatar"
				:image="row.avatar.image || undefined"
				:label="row.avatar.label"
				size="xl"
				class="shrink-0"
			/>
			<span
				v-else
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
				<span v-if="row.detail" class="line-clamp-1 text-sm text-ink-gray-5">{{
					row.detail
				}}</span>
				<!-- On a phone the status and date have a line of their own. -->
				<span
					v-if="row.status || row.due?.text"
					class="flex items-center gap-2 text-sm sm:hidden"
				>
					<span
						v-if="row.status"
						class="inline-flex items-center gap-1"
						:class="STATUS_TEXT[row.theme] || STATUS_TEXT.gray"
						><span
							:class="STATUS_ICONS[row.theme] || STATUS_ICONS.gray"
							class="size-3.5"
							aria-hidden="true"
						/>{{ t(row.status) }}</span
					>
					<template v-if="row.due?.text">
						<span v-if="row.status" class="text-ink-gray-4" aria-hidden="true">·</span>
						<span
							:class="
								row.due.late ? 'font-medium text-ink-red-4' : 'text-ink-gray-6'
							"
							>{{ row.due.text }}</span
						>
					</template>
				</span>
			</span>
			<span
				v-for="(cell, index) in cells"
				:key="index"
				class="hidden w-40 shrink-0 truncate text-sm text-ink-gray-6 lg:block"
				>{{ cell || "—" }}</span
			>
			<span v-if="statusColumn" class="hidden w-36 shrink-0 sm:flex">
				<!-- Colour and an icon, never colour alone. -->
				<Badge v-if="row.status" :label="t(row.status)" :theme="row.theme">
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
				v-if="dateColumn"
				class="hidden w-28 shrink-0 text-right text-sm sm:block"
				:class="row.due?.late ? 'font-medium text-ink-red-4' : 'text-ink-gray-6'"
			>
				{{ row.due?.text }}
			</span>
		</component>
		<!-- A row's own actions sit beside its link, not inside it; under it on a phone. -->
		<div v-if="$slots.actions" class="shrink-0 pb-2 pl-14 pr-2 sm:pb-0 sm:pl-0">
			<slot name="actions" />
		</div>
	</div>
</template>

<script setup>
// One row of a list: what it is, its status and when. `cells` are a list's extra columns, shown
// on a computer under the headings RowList draws. A row links to `to` (a route) or `href` (a Desk
// page); one with neither is not a link (its actions are in the `actions` slot), and one without
// `status` shows no badge.
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { Avatar, Badge } from "frappe-ui";
import { kindTint } from "@/lib/areas";
import { STATUS_ICONS } from "@/lib/status";
import { KINDS } from "@/pages/myWork";

const props = defineProps({
	row: { type: Object, required: true },
	cells: { type: Array, default: () => [] },
	// False for lists that have no date column, or no status column.
	dateColumn: { type: Boolean, default: true },
	statusColumn: { type: Boolean, default: true },
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
