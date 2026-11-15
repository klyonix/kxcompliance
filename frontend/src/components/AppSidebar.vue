<template>
	<Sidebar v-model:collapsed="collapsed" collapsed-width="3.5rem">
		<SidebarHeader
			:title="boot.appName"
			:subtitle="boot.userFullname"
			:logo="boot.appLogo || undefined"
			:menu-items="menu"
		/>
		<!-- The rows keep a margin from the edges, so the open page's highlight never touches the
		border, expanded or collapsed. -->
		<div class="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2" data-tour="nav">
			<NotificationBell v-if="!checksOnly()" in-sidebar />
			<template v-for="section in sections" :key="section.route">
				<template v-if="section.route === 'Settings'">
					<!-- Collapsed to icons, the group has no room to open: the icon opens Settings. -->
					<SidebarItem
						v-if="collapsed"
						:label="section.label"
						:icon="section.icon"
						:route="{ name: 'Settings' }"
						:active="settingsOpen"
					/>
					<template v-else>
						<SidebarItem
							:label="section.label"
							:icon="section.icon"
							:aria-expanded="groupOpen"
							aria-controls="settings-pages"
							data-tour="settings-nav"
							@click="groupOpen = !groupOpen"
						>
							<template #suffix>
								<span
									class="mr-2 size-4 text-ink-gray-5"
									:class="
										groupOpen ? 'lucide-chevron-down' : 'lucide-chevron-right'
									"
									aria-hidden="true"
								/>
							</template>
						</SidebarItem>
						<div
							v-show="groupOpen"
							id="settings-pages"
							role="group"
							:aria-label="section.label"
							class="ml-4 flex flex-col gap-0.5 border-l border-outline-gray-2 pl-2"
						>
							<SidebarItem
								v-for="page in settingsPages"
								:key="page.route"
								:label="page.label"
								:route="{ name: page.route }"
								:active="isSettingsPageOpen(page, route.name)"
							>
								<template #prefix><span /></template>
							</SidebarItem>
						</div>
					</template>
				</template>
				<SidebarItem
					v-else
					:label="section.label"
					:route="{ name: section.route }"
					:suffix="
						section.count && counts[section.count]
							? String(counts[section.count])
							: undefined
					"
				>
					<template #prefix>
						<span
							:class="[section.icon, sectionTint(section.route).icon]"
							class="size-4"
							aria-hidden="true"
						/>
					</template>
				</SidebarItem>
			</template>
		</div>
		<SyncStatus v-if="!collapsed" class="px-2 pb-2" />
		<div class="px-2 pb-2">
			<SidebarCollapseToggle />
		</div>
	</Sidebar>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { Sidebar, SidebarCollapseToggle, SidebarHeader, SidebarItem } from "frappe-ui";
import { boot, checksOnly, mayUseDesk } from "@/boot";
import NotificationBell from "@/components/NotificationBell.vue";
import { isSettingsPageOpen, sections, settingsPagesFor, signOut } from "@/navigation";
import { clearOutbox, outbox } from "@/offline/outbox";
import { sectionTint } from "@/lib/areas";
import { counts } from "@/stores/work";
import SyncStatus from "./SyncStatus.vue";

const COLLAPSED_KEY = "kxcompliance:sidebar-collapsed";
const GROUP_KEY = "kxcompliance:settings-group-open";

const route = useRoute();
const settingsPages = settingsPagesFor({ firm: boot.accountType === "CA/CS Firm" });
const settingsOpen = computed(() =>
	settingsPages.some((page) => isSettingsPageOpen(page, route.name))
);

// Both choices are kept on this device, so the side bar looks the same after a reload.
const collapsed = ref(localStorage.getItem(COLLAPSED_KEY) === "1");
const groupOpen = ref(localStorage.getItem(GROUP_KEY) === "1" || settingsOpen.value);
watch(collapsed, (value) => localStorage.setItem(COLLAPSED_KEY, value ? "1" : "0"));
watch(groupOpen, (value) => localStorage.setItem(GROUP_KEY, value ? "1" : "0"));
// Opening a settings page from anywhere else (a link, a button) shows where it sits.
watch(settingsOpen, (open) => {
	if (open) groupOpen.value = true;
});

const menu = [
	mayUseDesk() && {
		label: "Open the Desk",
		icon: "lucide-app-window",
		onClick: () => (window.location.href = "/app/klyonix-compliance"),
	},
	{
		label: "Sign out",
		icon: "lucide-log-out",
		onClick: () =>
			signOut({ unsent: outbox.waiting + outbox.needsLook.length, clear: clearOutbox }),
	},
].filter(Boolean);
</script>
