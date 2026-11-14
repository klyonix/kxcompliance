<template>
	<Button
		variant="ghost"
		icon="lucide-circle-help"
		label="Tours and help"
		data-tour="help"
		@click="open = true"
	/>
	<Dialog v-model:open="open" title="Tours and help">
		<div class="flex flex-col gap-4">
			<p class="text-base text-ink-gray-6">
				Short walk-throughs of the page you are on and the others you use. Take any of them
				again whenever you like.
			</p>
			<p v-if="note" role="status" class="text-base text-ink-gray-8">{{ note }}</p>
			<div v-if="here" class="flex flex-col gap-1">
				<p class="text-xs font-medium uppercase tracking-wide text-ink-gray-5">
					This page
				</p>
				<Button
					class="justify-start"
					icon-left="lucide-play"
					:label="here.title"
					@click="take(here.id)"
				/>
			</div>
			<div v-if="others.length" class="flex flex-col gap-1">
				<p class="text-xs font-medium uppercase tracking-wide text-ink-gray-5">
					Every tour
				</p>
				<ul class="flex max-h-72 flex-col gap-1 overflow-y-auto">
					<li v-for="tour in others" :key="tour.id">
						<button
							type="button"
							class="w-full rounded-lg px-2 py-1.5 text-left text-base text-ink-gray-8 hover:bg-surface-gray-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4"
							@click="take(tour.id, tour.route)"
						>
							{{ tour.title }}
						</button>
					</li>
				</ul>
			</div>
			<div class="border-t border-outline-gray-1 pt-3">
				<Button
					class="w-full"
					icon-left="lucide-book-open"
					label="Open the user manual"
					@click="openManual"
				/>
			</div>
		</div>
	</Dialog>
</template>

<script setup>
// The question mark in every page's header: this page's tour, every other tour this person's
// menu offers, and the user manual. It also plays a page's tour by itself the first time someone
// opens that page.
import { computed, nextTick, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button, Dialog } from "frappe-ui";
import { tourFor } from "@/tours/tours";
import { autoStart, startTour, toursForReader } from "@/tours/useTours";

const route = useRoute();
const router = useRouter();
const open = ref(false);
const note = ref("");

const readable = computed(() => toursForReader());
const here = computed(() => {
	const tour = tourFor(String(route.name || ""));
	return tour && readable.value.some((allowed) => allowed.id === tour.id) ? tour : null;
});
const others = computed(() =>
	readable.value.filter((tour) => !tour.record && tour.id !== here.value?.id)
);

async function take(id, routeName) {
	note.value = "";
	open.value = false;
	if (routeName && routeName !== route.name) await router.push({ name: routeName });
	await nextTick();
	if (!(await startTour(id))) {
		// Said where they asked, rather than a press that seems to do nothing.
		note.value = "There is nothing on this page for that tour to show yet.";
		open.value = true;
	}
}

function openManual() {
	open.value = false;
	router.push({ name: "Help" });
}

watch(
	() => route.name,
	(name) => {
		if (name) autoStart(String(name)).catch(() => {});
	},
	{ flush: "post", immediate: true }
);
</script>
