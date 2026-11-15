<template>
	<ul class="grid grid-cols-2 gap-3 lg:grid-cols-4" data-tour="overview-tiles">
		<li
			v-for="tile in tiles"
			:key="tile.key"
			class="flex flex-col gap-2 rounded-xl p-4"
			:class="TILE_STYLES[tile.key].box"
		>
			<span
				class="flex items-center gap-2 text-sm font-medium"
				:class="TILE_STYLES[tile.key].ink"
			>
				<span :class="TILE_STYLES[tile.key].icon" class="size-4" aria-hidden="true" />
				{{ tile.label }}
			</span>
			<span class="text-3xl font-semibold tabular-nums text-ink-gray-9">{{
				tile.value
			}}</span>
			<!-- What the number is made of; each part opens the list of exactly those. -->
			<span class="flex flex-col gap-0.5 text-sm">
				<template v-for="part in tile.parts" :key="part.label">
					<RouterLink
						v-if="part.value && partRoute(part, tile)"
						:to="partRoute(part, tile)"
						class="flex justify-between gap-2 rounded text-ink-gray-7 hover:text-ink-gray-9 hover:underline"
					>
						<span class="truncate">{{ part.label }}</span>
						<span class="tabular-nums">{{ part.value }}</span>
					</RouterLink>
					<span v-else class="flex justify-between gap-2 text-ink-gray-5">
						<span class="truncate">{{ part.label }}</span>
						<span class="tabular-nums">{{ part.value }}</span>
					</span>
				</template>
			</span>
		</li>
	</ul>
</template>

<script setup>
// The Overview's first row: what is late, due this week, due in the month and waiting for review,
// across filings, licences and legal dates, each in a colour of its own.
import { RouterLink } from "vue-router";
import { listRoute } from "@/lib/listFilters";

defineProps({ tiles: { type: Array, required: true } });

const TILE_STYLES = {
	overdue: { box: "bg-surface-red-1", ink: "text-ink-red-5", icon: "lucide-circle-alert" },
	week: { box: "bg-surface-amber-1", ink: "text-ink-amber-6", icon: "lucide-clock" },
	month: { box: "bg-surface-blue-1", ink: "text-ink-blue-5", icon: "lucide-calendar-range" },
	review: { box: "bg-surface-violet-1", ink: "text-ink-violet-6", icon: "lucide-eye" },
};

const partRoute = (part, tile) =>
	listRoute({
		doctype: part.doctype,
		filters: part.filters,
		label: `${tile.label}: ${part.label}`,
	});
</script>
