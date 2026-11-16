<template>
	<Sidebar v-model:collapsed="collapsed" collapsed-width="3.5rem">
		<SidebarHeader :title="boot.appName" :subtitle="boot.userFullname" :menu-items="menu">
			<!-- Logos are mostly drawn for white paper: on a dark page one sits on a light tile. -->
			<template v-if="boot.appLogo" #prefix>
				<img
					:src="boot.appLogo"
					:alt="boot.appName"
					class="h-full w-full object-contain dark:rounded-[6px] dark:bg-white dark:p-0.5"
				/>
			</template>
		</SidebarHeader>
		<!-- The rows keep a margin from the edges, so the open page's highlight never touches the
		border, expanded or collapsed. They keep their height too: with Settings open the list
		scrolls instead of squeezing every row. -->
		<div
			class="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto px-2 [&>*]:shrink-0"
			data-tour="nav"
		>
			<NotificationBell v-if="!checksOnly()" in-sidebar />
			<template v-for="section in sections" :key="section.route">
				<!-- A group (Settings, and Clients with Client billing) opens to choose a page. -->
				<template v-if="pagesOf(section)">
					<!-- Collapsed to icons, the group has no room to open: the icon opens its first page. -->
					<SidebarItem
						v-if="collapsed"
						:label="t(section.label)"
						:route="{ name: section.route }"
						:active="isOpenIn(section)"
					>
						<template #prefix>
							<span
								:class="[section.icon, sectionTint(section.route).icon]"
								class="size-4"
								aria-hidden="true"
							/>
						</template>
					</SidebarItem>
					<template v-else>
						<SidebarItem
							:label="t(section.label)"
							:aria-expanded="Boolean(openGroups[section.route])"
							:aria-controls="`${section.route}-pages`"
							:data-tour="section.tour"
							@click="openGroups[section.route] = !openGroups[section.route]"
						>
							<template #prefix>
								<span
									:class="[section.icon, sectionTint(section.route).icon]"
									class="size-4"
									aria-hidden="true"
								/>
							</template>
							<template #suffix>
								<span
									class="mr-2 size-4 text-ink-gray-5"
									:class="
										openGroups[section.route]
											? 'lucide-chevron-down'
											: 'lucide-chevron-right'
									"
									aria-hidden="true"
								/>
							</template>
						</SidebarItem>
						<div
							v-show="openGroups[section.route]"
							:id="`${section.route}-pages`"
							role="group"
							:aria-label="t(section.label)"
							class="ml-4 flex flex-col gap-0.5 border-l border-outline-gray-2 pl-2"
						>
							<SidebarItem
								v-for="page in pagesOf(section)"
								:key="page.route"
								:label="t(page.label)"
								:route="{ name: page.route }"
								:active="isSettingsPageOpen(page, route.name)"
							>
								<template #prefix><span /></template>
							</SidebarItem>
						</div>
					</template>
				</template>
				<!-- Search opens quick search over the page, as Ctrl/⌘ K does. -->
				<SidebarItem
					v-else-if="section.route === 'Search'"
					:label="t(section.label)"
					:suffix="shortcut"
					:on-click="openSearch"
				>
					<template #prefix>
						<span
							:class="[section.icon, sectionTint(section.route).icon]"
							class="size-4"
							aria-hidden="true"
						/>
					</template>
				</SidebarItem>
				<SidebarItem
					v-else
					:label="t(section.label)"
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
import { reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { Sidebar, SidebarCollapseToggle, SidebarHeader, SidebarItem } from "frappe-ui";
import { boot, checksOnly, mayUseDesk } from "@/boot";
import NotificationBell from "@/components/NotificationBell.vue";
import { deskPath, isSettingsPageOpen, sections, settingsPagesFor, signOut } from "@/navigation";
import { clearOutbox, outbox } from "@/offline/outbox";
import { sectionTint } from "@/lib/areas";
import { paletteOpen, shortcutLabel } from "@/lib/quickSearch";
import { counts } from "@/stores/work";
import SyncStatus from "./SyncStatus.vue";

const COLLAPSED_KEY = "kxcompliance:sidebar-collapsed";

const route = useRoute();
const settingsPages = settingsPagesFor();
// Search opens quick search, with its keyboard shortcut beside it.
const shortcut = shortcutLabel();
const openSearch = () => (paletteOpen.value = true);

// The side bar's width is kept on this device, so it looks the same after a reload.
const collapsed = ref(localStorage.getItem(COLLAPSED_KEY) === "1");
watch(collapsed, (value) => localStorage.setItem(COLLAPSED_KEY, value ? "1" : "0"));
// A group's pages: Settings', and those a section carries (Clients with Client billing).
const pagesOf = (section) => (section.route === "Settings" ? settingsPages : section.pages);
const isOpenIn = (section) =>
	(pagesOf(section) || []).some((page) => isSettingsPageOpen(page, route.name));
// Each group (RK, 15 Nov 2026, for Settings): open while one of its pages is, a reload included,
// and closed again on leaving it. Its heading still opens it to choose a page.
const openGroups = reactive({});
watch(
	() => route.name,
	() => {
		for (const section of sections) {
			if (pagesOf(section)) openGroups[section.route] = isOpenIn(section);
		}
	},
	{ immediate: true }
);

const menu = [
	mayUseDesk() && {
		label: "Open the Desk",
		icon: "lucide-app-window",
		onClick: () => (window.location.href = deskPath("klyonix-compliance")),
	},
	{
		label: "Sign out",
		icon: "lucide-log-out",
		onClick: () =>
			signOut({ unsent: outbox.waiting + outbox.needsLook.length, clear: clearOutbox }),
	},
].filter(Boolean);
</script>
