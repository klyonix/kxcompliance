<template>
	<div class="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6">
		<FactsStrip v-if="facts.length" :facts="facts" class="mb-6" />
		<div class="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1fr)_22rem]">
			<div class="flex min-w-0 flex-col gap-8">
				<slot />
			</div>
			<!-- The activity sits beside the record on a computer, and under it on a phone. -->
			<aside v-if="doctype && name" class="lg:sticky lg:top-4 lg:self-start">
				<RecordActivity :key="`${doctype}:${name}`" :doctype="doctype" :name="name" />
			</aside>
		</div>
	</div>
</template>

<script setup>
// A record's page: its key facts across the top, the page itself, and its activity beside it.
// The activity (Frappe's timeline and its comment editor) is large, so it loads with the page
// rather than with the app, and is not kept for offline use.
import { defineAsyncComponent } from "vue";
import FactsStrip from "@/components/FactsStrip.vue";

const RecordActivity = defineAsyncComponent(() => import("@/components/RecordActivity.vue"));

defineProps({
	doctype: { type: String, default: "" },
	name: { type: String, default: "" },
	// [{ label, value, icon?, tone? }]
	facts: { type: Array, default: () => [] },
});
</script>
