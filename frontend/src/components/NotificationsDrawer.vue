<template>
	<Teleport to="body">
		<div v-if="panelOpen" class="fixed inset-0 z-40 flex justify-end">
			<div class="absolute inset-0 bg-black/20" aria-hidden="true" @click="close" />
			<aside
				class="relative flex h-full w-full flex-col overflow-y-auto bg-surface-base shadow-xl sm:w-[26rem]"
				role="dialog"
				aria-modal="true"
				aria-label="Notifications"
				@keydown.esc="close"
			>
				<NotificationPanel
					v-bind="feed"
					:tabs="TABS"
					@mark-as-read="open"
					@mark-all-as-read="feed.markAllAsRead"
					@load-more="feed.loadMore"
					@tab-change="feed.filterByTab"
					@close="close"
				/>
			</aside>
		</div>
	</Teleport>
</template>

<script setup>
// The notifications panel, sliding in from the right; a notification opens its record here.
import { useRouter } from "vue-router";
import { NotificationPanel } from "@framework/ui/components/Notifications/index.ts";
import { deskRoute } from "@/navigation";
import { recordRoute } from "@/lib/records";
import { notifications, panelOpen } from "@/stores/notifications";

const TABS = [
	{ label: "All", value: "all" },
	{ label: "Unread", value: "unread", filter: (n) => !n.read, count: "unread" },
];

const router = useRouter();
const feed = notifications();
const close = () => (panelOpen.value = false);

function open(notification) {
	feed.markAsRead(notification.name);
	close();
	const { document_type: doctype, document_name: name } = notification;
	if (!doctype) return;
	const to = recordRoute(doctype, name);
	if (to) router.push(to);
	else window.location.href = deskRoute(doctype, name);
}
</script>
