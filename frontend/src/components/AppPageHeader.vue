<template>
	<PageHeaderMobile v-if="isMobile">
		<template v-if="parent" #prefix>
			<Button
				variant="ghost"
				icon="lucide-arrow-left"
				:label="`Back to ${parent.label}`"
				@click="back"
			/>
		</template>
		<template v-else-if="showSearch" #prefix>
			<Button
				variant="ghost"
				icon="lucide-search"
				label="Search"
				:route="{ name: 'Search' }"
			/>
		</template>
		<PageHeaderMobileTitle :title="title" />
		<template #suffix><slot name="actions" /></template>
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
		<div class="flex items-center gap-2"><slot name="actions" /></div>
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
