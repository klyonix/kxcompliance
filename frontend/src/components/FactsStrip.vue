<template>
	<dl
		class="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-outline-gray-1 bg-surface-gray-3 sm:grid-cols-4"
		data-tour="record-facts"
	>
		<div
			v-for="fact in facts"
			:key="fact.label"
			class="flex flex-col gap-1 bg-surface-base px-4 py-3"
		>
			<dt class="flex items-center gap-1.5 text-xs font-medium text-ink-gray-5">
				<span v-if="fact.icon" :class="fact.icon" class="size-3.5" aria-hidden="true" />
				{{ fact.label }}
			</dt>
			<dd class="truncate text-base font-medium" :class="TONES[fact.tone] || TONES.plain">
				{{ fact.value || "—" }}
			</dd>
		</div>
	</dl>
</template>

<script setup>
// A record's key facts in one band: when, who, and for which company.
defineProps({ facts: { type: Array, required: true } });

const TONES = {
	plain: "text-ink-gray-8",
	red: "text-ink-red-4",
	amber: "text-ink-amber-6",
	green: "text-ink-green-6",
};
</script>
