<template>
	<Teleport to="body">
		<!-- It opens beside the side bar (from the left edge on a phone, which has none), and the
		     side bar stays usable while it is open. -->
		<div
			v-if="panelOpen"
			class="fixed inset-y-0 right-0 z-40 flex justify-start"
			:style="{ left: `${left}px` }"
		>
			<div class="absolute inset-0 bg-black/20" aria-hidden="true" @click="close" />
			<aside
				class="relative flex h-full w-full flex-col overflow-y-auto border-r border-outline-gray-1 bg-surface-base shadow-xl sm:w-[26rem]"
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
// The notifications panel, opening beside the side bar; a notification opens its record here.
import { onBeforeUnmount, ref, watch } from "vue";
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

// Where the side bar ends, followed as it is collapsed or expanded; 0 where there is none.
const left = ref(0);
const sidebar = () => document.querySelector('[data-slot="sidebar"]');
function measure() {
	const element = sidebar();
	left.value = element?.offsetParent ? Math.round(element.getBoundingClientRect().right) : 0;
}
const observer = new ResizeObserver(measure);
watch(
	panelOpen,
	(open) => {
		observer.disconnect();
		if (!open) return;
		measure();
		if (sidebar()) observer.observe(sidebar());
		observer.observe(document.body);
	},
	{ immediate: true }
);
onBeforeUnmount(() => observer.disconnect());

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
