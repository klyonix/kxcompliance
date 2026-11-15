<template>
	<div class="flex flex-wrap items-center gap-2" data-tour="list-filter">
		<QuickFilter
			v-model:filters="view.filters.conditions.value"
			v-model:fields="view.quickFilter.fields.value"
			v-model:customizing="view.quickFilter.customizing.value"
			:doctype="doctype"
		/>
		<template v-if="!view.quickFilter.customizing.value">
			<Filter v-model="view.filters.conditions.value" :doctype="doctype" />
			<SortBy v-model="view.sort.by.value" :doctype="doctype" />
			<ColumnSettings
				v-if="table"
				v-model="view.columns.shown.value"
				:doctype="doctype"
				:can-reset="view.columns.isCustomized.value"
				@reset="view.columns.reset()"
			/>
			<Button
				v-if="view.quickFilter.canCustomize.value"
				variant="ghost"
				icon="lucide-sliders-horizontal"
				label="Choose quick filters"
				@click="view.quickFilter.customizing.value = true"
			/>
		</template>
	</div>
</template>

<script setup>
// Frappe's own list controls (@framework/ui) for one record type: quick filters each person
// chooses, the full filter, the sort and, in the table, the columns. They read the type's fields
// from Frappe and keep their state in one snapshot, which the list saves and restores.
import { onMounted, watch } from "vue";
import { Button } from "frappe-ui";
import { ColumnSettings } from "@framework/ui/ColumnSettings";
import { Filter, serializeFilters } from "@framework/ui/Filter";
import { useListView } from "@framework/ui/ListView";
import { QuickFilter } from "@framework/ui/QuickFilter";
import { SortBy, serializeOrderBy } from "@framework/ui/SortBy";

const props = defineProps({
	doctype: { type: String, required: true },
	// A snapshot to start from: the person's last state on this device, or a saved view.
	state: { type: Object, default: null },
	// Whether the table is shown, which alone has columns to choose.
	table: { type: Boolean, default: false },
});
const emit = defineEmits(["change"]);

const view = useListView(props.doctype);

function report() {
	const snapshot = view.snapshot.value;
	emit("change", {
		snapshot,
		filters: serializeFilters(snapshot.filters),
		orderBy: snapshot.sort.length ? serializeOrderBy(snapshot.sort) : "",
		columns: snapshot.columns,
	});
}

onMounted(() => {
	if (props.state) view.restore(props.state);
	report();
});
watch(view.snapshot, report);
// A saved view chosen while the controls are open replaces what they show.
watch(
	() => props.state,
	(state) => {
		if (state) view.restore(state);
	}
);
</script>
