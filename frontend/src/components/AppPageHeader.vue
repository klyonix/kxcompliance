<template>
	<PageHeaderMobile v-if="isMobile">
		<template v-if="showSearch" #prefix>
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
		<PageHeaderTitle :title="title" />
		<div class="flex items-center gap-2"><slot name="actions" /></div>
	</PageHeader>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import {
	Button,
	PageHeader,
	PageHeaderMobile,
	PageHeaderMobileTitle,
	PageHeaderTitle,
} from "frappe-ui";
import { checksOnly } from "@/boot";
import { useIsMobile } from "@/composables/useIsMobile";

defineProps({ title: { type: String, required: true } });
const isMobile = useIsMobile();
const route = useRoute();
// Phones reach search from here; people who only check licences have nothing to search.
const showSearch = computed(() => route.name !== "Search" && !checksOnly());
</script>
