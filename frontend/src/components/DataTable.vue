<template>
	<!-- Wider than the page when many columns are chosen: it scrolls sideways, the page does not. -->
	<div class="-mx-3 overflow-x-auto" data-tour="list-table">
		<List
			:columns="template"
			class="list-row-px-3"
			:style="{ minWidth: `${minWidth}rem` }"
			divider="full"
		>
			<ListHeader>
				<ListHeaderCell v-for="column in columns" :key="column.fieldname">{{
					column.label
				}}</ListHeaderCell>
			</ListHeader>
			<ListRows :items="rows" row-key="key" v-slot="{ item }">
				<ListRow :route="item.to" class="py-[var(--row-pad)]">
					<ListCell v-for="(column, index) in columns" :key="column.fieldname">
						<span v-if="index === 0" class="flex min-w-0 items-center gap-2">
							<span
								class="flex size-6 shrink-0 items-center justify-center rounded-full"
								:class="kindTint(item.kind).tile"
							>
								<span
									:class="KINDS[item.kind]?.icon"
									class="size-3.5"
									aria-hidden="true"
								/>
							</span>
							<span class="truncate font-medium text-ink-gray-8">{{
								cell(item, column)
							}}</span>
						</span>
						<Badge
							v-else-if="column.fieldname === 'status'"
							:label="item.status"
							:theme="item.theme"
						>
							<template #prefix>
								<span
									:class="STATUS_ICONS[item.theme] || STATUS_ICONS.gray"
									class="size-3"
									aria-hidden="true"
								/>
							</template>
						</Badge>
						<span
							v-else
							class="truncate text-ink-gray-7"
							:class="{ 'text-right': isNumber(item.record[column.fieldname]) }"
							>{{ cell(item, column) }}</span
						>
					</ListCell>
				</ListRow>
			</ListRows>
		</List>
	</div>
</template>

<script setup>
// The Table layout: the columns the person chose, one line per record, a line between rows.
import { computed } from "vue";
import { Badge } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";
import { nameOf } from "@/composables/usePeople";
import { kindTint } from "@/lib/areas";
import { formatDate } from "@/lib/format";
import { PERSON_FIELDS, columnTrack, tableMinWidth } from "@/lib/table";
import { STATUS_ICONS } from "@/lib/status";
import { KINDS } from "@/pages/myWork";

const props = defineProps({
	// [{ fieldname, label, width? }], from ColumnSettings.
	columns: { type: Array, required: true },
	// Rows as the list builds them, with the record they came from.
	rows: { type: Array, required: true },
});

const template = computed(() => props.columns.map((column, index) => columnTrack(column, index)));
const minWidth = computed(() => tableMinWidth(props.columns));
const isNumber = (value) => typeof value === "number";

function cell(item, column) {
	const value = item.record[column.fieldname];
	if (value === null || value === undefined || value === "") return "—";
	if (PERSON_FIELDS.includes(column.fieldname)) return nameOf(value);
	if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}( |$)/.test(value))
		return formatDate(value);
	if (value === 0 || value === 1) {
		if (column.fieldname.startsWith("is_") || column.fieldname.endsWith("_missing")) {
			return value ? "Yes" : "No";
		}
	}
	return String(value);
}
</script>
