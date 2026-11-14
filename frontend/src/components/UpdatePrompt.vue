<template>
	<div
		v-if="update.ready"
		role="status"
		class="mx-4 mt-3 flex items-center gap-3 rounded-lg bg-surface-blue-1 px-3 py-2 text-base text-ink-blue-7 sm:mx-6"
	>
		<span class="lucide-sparkles size-4 shrink-0" aria-hidden="true" />
		<span class="flex-1">A new version of the app is ready.</span>
		<Button variant="solid" label="Reload" @click="applyUpdate()" />
	</div>
</template>

<script setup>
import { Button } from "frappe-ui";
import { applyUpdate, update } from "@/offline/updates";
</script>
