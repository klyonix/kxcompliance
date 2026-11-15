<template>
	<Dialog
		:open="open"
		:title="links.length > 1 ? 'Send them these links' : 'Send them this link'"
		:actions="
			links.length === 1
				? [{ label: 'Copy link', variant: 'solid', onClick: () => copy(links[0].url) }]
				: []
		"
		@update:open="emit('update:open', $event)"
	>
		<div class="flex flex-col gap-3">
			<p class="text-base text-ink-gray-7">
				This site cannot send email yet, so pass
				{{ links.length > 1 ? "each link" : "this link" }} on yourself, by WhatsApp or
				email. It lets them set a password and sign in, and works once.
			</p>
			<div v-for="link in links" :key="link.url" class="flex flex-col gap-1">
				<div v-if="links.length > 1" class="flex items-center justify-between gap-2">
					<span class="text-base font-medium text-ink-gray-8">{{ link.name }}</span>
					<Button
						variant="ghost"
						icon-left="lucide-copy"
						label="Copy"
						@click="copy(link.url)"
					/>
				</div>
				<p
					class="break-all rounded-lg bg-surface-gray-2 px-3 py-2 font-mono text-sm text-ink-gray-8"
				>
					{{ link.url }}
				</p>
			</div>
			<p class="text-sm text-ink-gray-5">
				Once an email account is set up in Settings, new people get their invitation by
				email.
			</p>
		</div>
	</Dialog>
</template>

<script setup>
// A one-time link to set a password, for a site that cannot email the invitation yet.
import { Button, Dialog, toast } from "frappe-ui";

defineProps({
	open: { type: Boolean, default: false },
	// [{ name, url }]
	links: { type: Array, required: true },
});
const emit = defineEmits(["update:open"]);

async function copy(url) {
	await navigator.clipboard.writeText(url);
	toast.success("Link copied");
}
</script>
