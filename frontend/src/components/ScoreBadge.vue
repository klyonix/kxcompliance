<template>
	<span
		class="inline-flex size-9 shrink-0 items-center justify-center rounded-full text-sm font-semibold"
		:class="TONES[scoreTone(score)]"
		role="img"
		:aria-label="score === null ? 'No score yet' : `Compliance score ${score} of 100`"
		>{{ score ?? "—" }}</span
	>
</template>

<script setup>
// A company's compliance score, in the colour of how it stands.
import { scoreTone } from "@/lib/score";

defineProps({ score: { type: Number, default: null } });

const TONES = {
	green: "bg-surface-green-2 text-ink-green-7",
	amber: "bg-surface-amber-2 text-ink-amber-7",
	red: "bg-surface-red-2 text-ink-red-7",
	gray: "bg-surface-gray-2 text-ink-gray-6",
};
</script>
