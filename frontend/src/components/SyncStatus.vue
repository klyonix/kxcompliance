<template>
	<div class="flex items-center gap-2 text-sm text-ink-gray-6" role="status">
		<span class="size-2 shrink-0 rounded-full" :class="dot" aria-hidden="true" />
		<span class="truncate">{{ text }}</span>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { connection, outbox } from "@/offline/outbox";

const plural = (count, word) => `${count} ${word}${count === 1 ? "" : "s"}`;
const waiting = (prefix) => (outbox.waiting ? `${prefix}, ${outbox.waiting} waiting` : prefix);

const text = computed(
	() =>
		({
			needsLook: `${plural(outbox.needsLook.length, "change")} ${
				outbox.needsLook.length === 1 ? "needs" : "need"
			} a look`,
			offline: waiting("Offline"),
			serverDown: waiting("Server not answering"),
			sending: `Sending ${plural(outbox.waiting, "change")}`,
			saved: "All changes saved",
		}[connection.value])
);
const dot = computed(
	() =>
		({
			needsLook: "bg-surface-red-5",
			saved: "bg-surface-green-5",
		}[connection.value] || "bg-surface-amber-5")
);
</script>
