<template>
	<div class="flex flex-col" data-tour="list-rows">
		<!-- Column headings on a computer; a phone shows each row's status under its title. -->
		<div
			class="hidden items-center gap-3 border-b border-outline-gray-1 px-3 pb-2 text-xs font-medium text-ink-gray-5 sm:flex"
			aria-hidden="true"
		>
			<span class="w-8 shrink-0" />
			<span class="flex-1">{{ t(nameLabel) }}</span>
			<!-- Extra columns from a wide screen; between that and a phone the name has the room. -->
			<span
				v-for="column in columns"
				:key="column.label"
				class="hidden w-40 shrink-0 lg:block"
				>{{ t(column.label) }}</span
			>
			<span v-if="statusLabel !== null" class="w-36 shrink-0">{{ t(statusLabel) }}</span>
			<span v-if="dateLabel !== null" class="w-28 shrink-0 text-right">{{
				t(dateLabel)
			}}</span>
			<!-- Over each row's actions (WorkRow keeps them in a column this wide, plus pr-2). -->
			<span v-if="withActions" class="shrink-0 pr-2" :class="actionsWidth" />
		</div>
		<template v-for="group in groups" :key="group.key">
			<h2
				v-if="group.label"
				class="flex items-center gap-2 px-3 pb-1 pt-4 text-sm font-semibold"
				:class="group.key === 'overdue' ? 'text-ink-red-4' : 'text-ink-gray-7'"
			>
				{{ t(group.label) }}
				<span class="font-normal text-ink-gray-5">{{ group.rows.length }}</span>
			</h2>
			<div class="flex flex-col [&>*+*]:border-t [&>*+*]:border-outline-gray-1">
				<WorkRow
					v-for="entry in group.rows"
					:key="entry.key"
					:row="entry"
					:cells="entry.cells"
					:date-column="dateLabel !== null"
					:status-column="statusLabel !== null"
				>
					<template v-if="withActions" #actions>
						<div class="flex items-center gap-2 sm:justify-end" :class="actionsWidth">
							<slot name="actions" :row="entry" />
						</div>
					</template>
				</WorkRow>
			</div>
		</template>
	</div>
</template>

<script setup>
// The rows of a list under their column headings, in groups when it has them: what RecordList
// shows in its List layout, and what lists that load from their own server call show.
import { computed, useSlots } from "vue";
import WorkRow from "@/components/WorkRow.vue";

const props = defineProps({
	// [{ key, label, rows }]; one group with no label for a plain list.
	groups: { type: Array, default: null },
	// Used when there are no groups.
	rows: { type: Array, default: () => [] },
	// [{ label }]: the headings of each row's `cells`.
	columns: { type: Array, default: () => [] },
	nameLabel: { type: String, default: "Name" },
	// null for a list without a status column.
	statusLabel: { type: String, default: "Status" },
	// null for a list without a date column.
	dateLabel: { type: String, default: "Date" },
	// The width of the actions column on a computer, as a Tailwind class written out where the
	// list is used (a phone puts the actions under the row).
	actionsWidth: { type: String, default: "sm:w-8" },
});

const slots = useSlots();
const withActions = computed(() => Boolean(slots.actions));
const groups = computed(() => props.groups || [{ key: "all", label: "", rows: props.rows }]);
</script>
