<template>
	<div class="mx-auto w-full px-4 py-6 sm:px-6" :class="recordWidth(name, { client })">
		<FactsStrip v-if="facts.length" :facts="facts" class="mb-6" />
		<div
			class="grid grid-cols-1 gap-8"
			:class="{ 'lg:grid-cols-[minmax(0,1fr)_22rem]': withActivity }"
		>
			<div class="flex min-w-0 flex-col gap-8">
				<slot />
			</div>
			<!-- The activity sits beside the record on a computer, and under it on a phone. -->
			<!-- The team's comments and history are for the team: a client's login does not see them. -->
			<aside v-if="withActivity" class="lg:sticky lg:top-4 lg:self-start">
				<RecordActivity :key="`${doctype}:${name}`" :doctype="doctype" :name="name" />
			</aside>
		</div>
	</div>
</template>

<script setup>
// A record's page: its key facts across the top, the page itself, and its activity beside it.
// A record not saved yet (a new one's form) has no activity, and keeps to a single column.
// The activity (Frappe's timeline and its comment editor) is large, so it loads with the page
// rather than with the app, and is not kept for offline use.
import { computed, defineAsyncComponent } from "vue";
import { isClientLogin } from "@/boot";
import FactsStrip from "@/components/FactsStrip.vue";
import { recordWidth, showsActivity } from "@/lib/records";

const RecordActivity = defineAsyncComponent(() => import("@/components/RecordActivity.vue"));

const props = defineProps({
	doctype: { type: String, default: "" },
	name: { type: String, default: "" },
	// [{ label, value, icon?, tone? }]
	facts: { type: Array, default: () => [] },
});

const client = isClientLogin();
const withActivity = computed(
	() => Boolean(props.doctype) && showsActivity(props.name, { client })
);
</script>
