<template>
	<MobileShell v-if="isMobile">
		<UpdatePrompt />
		<ConnectionBanner />
		<RouterView />
		<template #nav>
			<MobileNav>
				<MobileNavItem
					v-for="section in tabSections"
					:key="section.route"
					:label="section.tabLabel || section.label"
					:icon="section.icon"
					:route="{ name: section.route }"
				/>
				<MobileNavItem label="Account" :route="{ name: 'Account' }">
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
import { boot } from "./boot";
import AppSidebar from "./components/AppSidebar.vue";
import ConnectionBanner from "./components/ConnectionBanner.vue";
import UpdatePrompt from "./components/UpdatePrompt.vue";
import { useIsMobile } from "./composables/useIsMobile";
import { sections } from "./navigation";

// Paint the app light or dark as chosen on the Account page, following the system by default.
useColorScheme();
const isMobile = useIsMobile();
const tabSections = sections.filter((section) => !section.desktopOnly);
</script>
