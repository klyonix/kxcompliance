<template>
	<SidebarItem
		v-if="inSidebar"
		:label="t('Notifications')"
		icon="lucide-bell"
		:suffix="feed.unreadCount ? String(feed.unreadCount) : undefined"
		data-tour="notifications"
		@click="openPanel"
	/>
	<span v-else class="relative inline-flex">
		<Button
			variant="ghost"
			icon="lucide-bell"
			:label="
				feed.unreadCount
					? t('Notifications, {0} unread', feed.unreadCount)
					: t('Notifications')
			"
			data-tour="notifications"
			@click="openPanel"
		/>
		<span
			v-if="feed.unreadCount"
			class="pointer-events-none absolute right-1 top-1 size-2 rounded-full bg-surface-red-5"
			aria-hidden="true"
		/>
	</span>
</template>

<script setup>
// The bell: the number of unread notifications, opening the panel.
import { Button, SidebarItem } from "frappe-ui";
import { notifications, openPanel } from "@/stores/notifications";

defineProps({ inSidebar: { type: Boolean, default: false } });
const feed = notifications();
</script>
