<template>
	<PageHeaderMobile v-if="isMobile">
		<!-- Help sits on the left on a phone, so the page's own buttons keep room on the right. -->
		<template #prefix>
			<Button
				v-if="parent"
				variant="ghost"
				icon="lucide-arrow-left"
				:label="`Back to ${parent.label}`"
				@click="back"
			/>
			<Button
				v-else-if="showSearch"
				variant="ghost"
				icon="lucide-search"
				label="Search"
				:route="{ name: 'Search' }"
			/>
			<NotificationBell v-if="!checksOnly()" />
			<TourMenu />
		</template>
		<PageHeaderMobileTitle :title="title" />
		<template #suffix>
			<span v-if="$slots.actions" class="flex items-center" data-tour="page-actions">
				<slot name="actions" />
			</span>
		</template>
	</PageHeaderMobile>
	<PageHeader v-else>
		<div v-if="parent" class="flex min-w-0 items-center gap-2">
			<Button
				variant="ghost"
				icon="lucide-arrow-left"
				:label="`Back to ${parent.label}`"
				@click="back"
			/>
			<Breadcrumbs
				:items="[{ label: parent.label, route: parent.route }, { label: title }]"
			/>
		</div>
		<PageHeaderTitle v-else :title="title" />
		<div class="flex items-center gap-2">
			<span v-if="$slots.actions" class="flex items-center gap-2" data-tour="page-actions">
				<slot name="actions" />
			</span>
			<TourMenu />
		</div>
	</PageHeader>
</template>

<script setup>
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
	Breadcrumbs,
	Button,
	PageHeader,
	PageHeaderMobile,
	PageHeaderMobileTitle,
	PageHeaderTitle,
} from "frappe-ui";
import { checksOnly } from "@/boot";
import NotificationBell from "@/components/NotificationBell.vue";
import TourMenu from "@/components/TourMenu.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { goBack } from "@/navigation";

const props = defineProps({
	title: { type: String, required: true },
	// The list or page a record belongs to, { label, route }: shown as a back arrow, and on a
	// computer as a trail.
	parent: { type: Object, default: null },
});
const isMobile = useIsMobile();
const route = useRoute();
const router = useRouter();
// Phones reach search from here; people who only check licences have nothing to search.
const showSearch = computed(() => route.name !== "Search" && !checksOnly());
const back = () => goBack(router, props.parent.route);
</script>
