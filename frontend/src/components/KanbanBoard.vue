<template>
	<p v-if="!lanes" class="py-8 text-center text-base text-ink-gray-5" aria-busy="true">
		Loading the board…
	</p>
	<!-- Columns side by side, scrolling sideways; on a phone each column is most of the screen. -->
	<div
		v-else
		class="-mx-4 flex gap-3 overflow-x-auto px-4 pb-3 sm:mx-0 sm:px-0"
		data-tour="kanban"
	>
		<section
			v-for="lane in lanes"
			:key="lane.value"
			class="flex w-[85vw] shrink-0 flex-col rounded-lg bg-surface-gray-1 sm:w-72"
			:aria-label="`${lane.label}, ${lane.cards.length}`"
		>
			<h2
				class="flex items-center gap-2 rounded-t-lg border-t-4 px-3 py-2 text-sm font-semibold text-ink-gray-8"
				:class="LANE_BORDERS[lane.hue] || LANE_BORDERS.gray"
			>
				<span class="truncate">{{ lane.label }}</span>
				<span class="font-normal text-ink-gray-5">{{ lane.cards.length }}</span>
			</h2>
			<Draggable
				:list="lane.cards"
				item-key="key"
				group="kanban"
				:disabled="!board.movable"
				:data-lane="lane.value"
				class="flex min-h-16 flex-1 flex-col gap-2 p-2"
				ghost-class="opacity-40"
				@end="dropped"
			>
				<template #item="{ element }">
					<article
						class="relative flex flex-col gap-1.5 rounded-lg border border-outline-gray-1 bg-surface-base p-3 shadow-sm"
						:class="board.movable ? 'cursor-grab active:cursor-grabbing' : ''"
						:data-key="element.key"
					>
						<RouterLink
							:to="element.to"
							class="text-base font-medium text-ink-gray-8 after:absolute after:inset-0 hover:underline"
							>{{ element.title }}</RouterLink
						>
						<span class="line-clamp-2 text-sm text-ink-gray-5">{{
							element.detail
						}}</span>
						<span class="flex items-center justify-between gap-2 text-sm">
							<span
								class="inline-flex items-center gap-1"
								:class="STATUS_TEXT[element.theme] || STATUS_TEXT.gray"
								><span
									:class="STATUS_ICONS[element.theme] || STATUS_ICONS.gray"
									class="size-3.5"
									aria-hidden="true"
								/>{{ element.status }}</span
							>
							<span
								:class="
									element.due.late
										? 'font-medium text-ink-red-4'
										: 'text-ink-gray-6'
								"
								>{{ element.due.text }}</span
							>
						</span>
						<!-- Dragging does not work on touch screens: the menu moves a card too. -->
						<Dropdown
							v-if="board.movable"
							class="relative self-end"
							:options="moveOptions(element, lane)"
						>
							<Button
								size="sm"
								variant="ghost"
								icon="lucide-arrow-right-left"
								:label="`Move ${element.title}`"
							/>
						</Dropdown>
					</article>
				</template>
			</Draggable>
		</section>
	</div>
</template>

<script setup>
// A Kanban board of a list's records: a column per value of the board's field. Moving a card,
// by dragging or from its menu, asks the list to save the new value; a refused move puts the
// card back.
import { ref, watch } from "vue";
import { RouterLink } from "vue-router";
import Draggable from "vuedraggable";
import { Button, Dropdown } from "frappe-ui";
import { boardColumns, groupCards } from "@/lib/boards";
import { STATUS_ICONS } from "@/lib/status";

const props = defineProps({
	board: { type: Object, required: true },
	// Rows as the list builds them, with the record they came from.
	cards: { type: Array, required: true },
});
const emit = defineEmits(["move"]);

const LANE_BORDERS = {
	red: "border-outline-red-3",
	amber: "border-outline-amber-3",
	blue: "border-outline-blue-3",
	green: "border-outline-green-3",
	violet: "border-outline-violet-3",
	teal: "border-outline-teal-3",
	gray: "border-outline-gray-3",
};
const STATUS_TEXT = {
	red: "text-ink-red-4",
	amber: "text-ink-amber-4",
	blue: "text-ink-blue-4",
	green: "text-ink-green-4",
	gray: "text-ink-gray-6",
};

const columns = ref(null);
const lanes = ref(null);

async function build() {
	columns.value = columns.value || (await boardColumns(props.board));
	lanes.value = groupCards(props.cards, columns.value, props.board.field);
}

function dropped(event) {
	const from = event.from.dataset.lane;
	const to = event.to.dataset.lane;
	const key = event.item.dataset.key;
	const card = props.cards.find((entry) => entry.key === key);
	if (card) emit("move", { card, from, to, undo: build });
}

function moveOptions(card, lane) {
	return columns.value
		.filter((column) => column.value !== lane.value)
		.map((column) => ({
			label: `Move to ${column.label}`,
			onClick: () => emit("move", { card, from: lane.value, to: column.value, undo: build }),
		}));
}

// The columns are worked out once per board (the people, for a board by person); the cards are
// placed again whenever they change.
watch(
	() => props.board,
	() => {
		columns.value = null;
		build();
	},
	{ immediate: true }
);
watch(() => props.cards, build);
</script>
