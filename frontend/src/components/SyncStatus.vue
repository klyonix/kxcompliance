<template>
	<div class="flex items-center gap-2 text-sm text-ink-gray-6" role="status">
		<span class="size-2 shrink-0 rounded-full" :class="dot" aria-hidden="true" />
		<span class="truncate">{{ text }}</span>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { outbox } from "@/offline/outbox";
import { server } from "@/offline/reachability";

const plural = (count, word) => `${count} ${word}${count === 1 ? "" : "s"}`;

const text = computed(() => {
	if (outbox.needsLook.length) return `${plural(outbox.needsLook.length, "change")} need a look`;
	if (!outbox.online) return outbox.waiting ? `Offline, ${outbox.waiting} waiting` : "Offline";
	if (!server.reachable) {
		return outbox.waiting
			? `Server not answering, ${outbox.waiting} waiting`
			: "Server not answering";
	}
	if (outbox.sending || outbox.waiting) return `Sending ${plural(outbox.waiting, "change")}`;
	return "All changes saved";
});
const dot = computed(() => {
	if (outbox.needsLook.length) return "bg-surface-red-5";
	if (!outbox.online || !server.reachable || outbox.waiting) return "bg-surface-amber-5";
	return "bg-surface-green-5";
});
</script>
