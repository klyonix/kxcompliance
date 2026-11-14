<template>
	<Sidebar>
		<SidebarHeader
			:title="boot.appName"
			:subtitle="boot.userFullname"
			:logo="boot.appLogo || undefined"
			:menu-items="menu"
		/>
		<div class="flex flex-1 flex-col overflow-y-auto">
			<SidebarItem
				v-for="section in sections"
				:key="section.route"
				:label="section.label"
				:icon="section.icon"
				:route="{ name: section.route }"
				:suffix="
					section.count && counts[section.count]
						? String(counts[section.count])
						: undefined
				"
			/>
		</div>
		<SyncStatus class="px-2 pb-2" />
	</Sidebar>
</template>

<script setup>
import { Sidebar, SidebarHeader, SidebarItem } from "frappe-ui";
import { boot, mayUseDesk } from "@/boot";
import { sections, signOut } from "@/navigation";
import { clearOutbox, outbox } from "@/offline/outbox";
import { counts } from "@/stores/work";
import SyncStatus from "./SyncStatus.vue";

const menu = [
	mayUseDesk() && {
		label: "Open the Desk",
		icon: "lucide-app-window",
		onClick: () => (window.location.href = "/app/compliance-plus"),
	},
	{
		label: "Sign out",
		icon: "lucide-log-out",
		onClick: () =>
			signOut({ unsent: outbox.waiting + outbox.needsLook.length, clear: clearOutbox }),
	},
].filter(Boolean);
</script>
