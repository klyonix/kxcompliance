<template>
	<aside
		class="fixed bottom-20 right-4 z-50 flex w-64 flex-col gap-3 rounded-xl bg-surface-base p-3 shadow-2xl ring-1 ring-outline-gray-2 sm:bottom-4"
		aria-label="Design variations"
	>
		<p class="text-sm font-semibold text-ink-gray-8">Tweaks</p>
		<label class="flex flex-col gap-1.5 text-sm text-ink-gray-6">
			Spacing
			<TabButtons
				v-model="tweaks.density"
				fluid
				:options="[
					{ label: 'Compact', value: 'compact' },
					{ label: 'Relaxed', value: 'relaxed' },
				]"
			/>
		</label>
		<label class="flex flex-col gap-1.5 text-sm text-ink-gray-6">
			Group My Work by
			<TabButtons
				v-model="tweaks.grouping"
				fluid
				:options="[
					{ label: 'When due', value: 'date' },
					{ label: 'Kind', value: 'kind' },
				]"
			/>
		</label>
	</aside>
</template>

<script setup>
import { TabButtons } from "frappe-ui";
import { tweaks } from "@/stores/tweaks";
</script>
