<template>
	<!-- Onboarding, and the privacy notice before it is accepted, have the whole screen: there is
	nothing to navigate to until they are done. Re-read from Account, the notice is a normal page. -->
	<RouterView
		v-if="route.name === 'Onboarding' || (route.name === 'PrivacyNotice' && route.query.next)"
	/>
	<MobileShell v-else-if="isMobile">
		<NotificationsDrawer />
		<UpdatePrompt />
		<ConnectionBanner />
		<RouterView />
		<template #nav>
			<MobileNav data-tour="nav">
				<MobileNavItem
					v-for="section in tabSections"
					:key="section.route"
					:label="t(section.tabLabel || section.label)"
					:icon="section.icon"
					:route="{ name: section.route }"
				/>
				<MobileNavItem :label="t('Account')" :route="{ name: 'Account' }">
					<template #default="{ active }">
						<Avatar
							:label="boot.userFullname || boot.user"
							size="sm"
							:class="active ? 'ring-2 ring-outline-gray-4' : ''"
						/>
					</template>
				</MobileNavItem>
			</MobileNav>
		</template>
	</MobileShell>

	<DesktopShell v-else>
		<template #sidebar>
			<AppSidebar />
		</template>
		<NotificationsDrawer />
		<UpdatePrompt />
		<ConnectionBanner />
		<RouterView />
	</DesktopShell>
</template>

<script setup>
import {
	Avatar,
	DesktopShell,
	MobileNav,
	MobileNavItem,
	MobileShell,
	useColorScheme,
} from "frappe-ui";
import { onBeforeUnmount, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { boot, checksOnly } from "./boot";
import AppSidebar from "./components/AppSidebar.vue";
import NotificationsDrawer from "./components/NotificationsDrawer.vue";
import ConnectionBanner from "./components/ConnectionBanner.vue";
import UpdatePrompt from "./components/UpdatePrompt.vue";
import { useIsMobile } from "./composables/useIsMobile";
import { sections } from "./navigation";

// Paint the app light or dark as chosen on the Account page, following the system by default.
useColorScheme();

// Ctrl/⌘ K anywhere, or "/" when not typing, opens search.
const router = useRouter();
const route = useRoute();
function openSearch(event) {
	const typing = event.target.closest?.("input, textarea, select, [contenteditable]");
	const shortcut =
		((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") ||
		(event.key === "/" && !typing);
	if (!shortcut || checksOnly()) return;
	event.preventDefault();
	router.push({ name: "Search" });
}
onMounted(() => window.addEventListener("keydown", openSearch));
onBeforeUnmount(() => window.removeEventListener("keydown", openSearch));
const isMobile = useIsMobile();
const tabSections = sections.filter((section) => !section.desktopOnly);
</script>
