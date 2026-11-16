<template>
	<div
		v-for="notice in boot.notices"
		:key="notice.text"
		role="status"
		class="mx-4 mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg px-3 py-2 text-base sm:mx-6"
		:class="TONES[notice.theme] || TONES.gray"
	>
		<span>{{ notice.text }}</span>
		<a
			v-if="notice.link_url && notice.link_label"
			:href="notice.link_url"
			class="font-medium underline underline-offset-2"
			>{{ notice.link_label }}</a
		>
	</div>
</template>

<script setup>
// Notices other apps on the site add to the app (kxcompliance_boot), such as a trial ending.
import { boot } from "@/boot";

const TONES = {
	red: "bg-surface-red-1 text-ink-red-7",
	amber: "bg-surface-amber-1 text-ink-amber-7",
	blue: "bg-surface-blue-1 text-ink-blue-7",
	gray: "bg-surface-gray-2 text-ink-gray-7",
};
</script>
