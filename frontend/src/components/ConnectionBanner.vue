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
import { connection, outbox } from "@/offline/outbox";

// Shown only when something differs from normal: offline, the server not answering, or a
// change that needs a second look. The state itself comes from offline/outbox.js.
const plural = (count, word) => `${count} ${word}${count === 1 ? "" : "s"}`;
const sentWhen = (when, otherwise = "") =>
	outbox.waiting ? ` ${plural(outbox.waiting, "change")} will be sent ${when}.` : otherwise;

const message = computed(
	() =>
		({
			needsLook: `${plural(
				outbox.needsLook.length,
				"change"
			)} made offline could not be saved as made. Open Account to look at them.`,
			offline: `You are offline and seeing what was last loaded.${sentWhen(
				"when you reconnect"
			)}`,
			serverDown: `The server is not answering, so you are seeing what was last loaded.${sentWhen(
				"when it is back",
				" Changes you make are kept on this device and sent when it is back."
			)}`,
		}[connection.value] || "")
);
const tone = computed(() =>
	connection.value === "needsLook"
		? "bg-surface-red-1 text-ink-red-7"
		: "bg-surface-amber-1 text-ink-amber-7"
);
const icon = computed(
	() =>
		({
			needsLook: "lucide-triangle-alert",
			offline: "lucide-wifi-off",
			serverDown: "lucide-server-off",
		}[connection.value])
);
</script>
