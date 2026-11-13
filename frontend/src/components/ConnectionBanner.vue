<template>
	<div
		v-if="message"
		role="status"
		class="mx-4 mt-3 flex items-start gap-2 rounded-lg px-3 py-2 text-base sm:mx-6"
		:class="tone"
	>
		<span :class="icon" class="mt-0.5 size-4 shrink-0" aria-hidden="true" />
		<span>{{ message }}</span>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { outbox } from "@/offline/outbox";

// Shown only when something differs from normal: offline, or a change that needs a second look.
const plural = (count, word) => `${count} ${word}${count === 1 ? "" : "s"}`;

const message = computed(() => {
	if (outbox.needsLook.length) {
		return `${plural(
			outbox.needsLook.length,
			"change"
		)} made offline could not be saved as made. Open Account to look at them.`;
	}
	if (!outbox.online) {
		const waiting = outbox.waiting
			? ` ${plural(outbox.waiting, "change")} will be sent when you reconnect.`
			: "";
		return `You are offline and seeing what was last loaded.${waiting}`;
	}
	return "";
});
const tone = computed(() =>
	outbox.needsLook.length
		? "bg-surface-red-1 text-ink-red-4"
		: "bg-surface-amber-1 text-ink-amber-4"
);
const icon = computed(() =>
	outbox.needsLook.length ? "lucide-triangle-alert" : "lucide-wifi-off"
);
</script>
