<template>
	<section
		class="flex flex-col gap-2"
		aria-labelledby="recent-heading"
		data-tour="overview-recent"
	>
		<h2 id="recent-heading" class="text-base font-semibold text-ink-gray-8">Recent changes</h2>
		<p v-if="!entries.length" class="text-sm text-ink-gray-5">Nothing has changed lately.</p>
		<ul v-else class="flex flex-col">
			<li v-for="entry in entries" :key="`${entry.doctype}-${entry.name}`">
				<RouterLink
					:to="recordRoute(entry.doctype, entry.name) || '/'"
					class="flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-surface-gray-2"
				>
					<span
						class="flex size-7 shrink-0 items-center justify-center rounded-full"
						:class="kindTint(KIND_OF[entry.doctype]).tile"
					>
						<span
							:class="KINDS[KIND_OF[entry.doctype]]?.icon"
							class="size-3.5"
							aria-hidden="true"
						/>
					</span>
					<span class="flex min-w-0 flex-col">
						<span class="truncate text-sm font-medium text-ink-gray-8">{{
							entry.title
						}}</span>
						<span class="truncate text-xs text-ink-gray-5"
							>{{ nameOf(entry.by) }} · {{ formatDateTime(entry.on) }}</span
						>
					</span>
				</RouterLink>
			</li>
		</ul>
	</section>
</template>

<script setup>
// The latest changes to the records the person may read, with who made them.
import { onMounted } from "vue";
import { RouterLink } from "vue-router";
import { learnNames, nameOf } from "@/composables/usePeople";
import { kindTint } from "@/lib/areas";
import { formatDateTime } from "@/lib/format";
import { recordRoute } from "@/lib/records";
import { KINDS } from "@/pages/myWork";

const props = defineProps({ entries: { type: Array, required: true } });

const KIND_OF = {
	"Compliance Item": "licence",
	"Compliance Task": "filing",
	"Legal Case": "legal",
	Trademark: "trademark",
	"Document Request": "request",
};

onMounted(() => learnNames(props.entries.map((entry) => entry.by)));
</script>
