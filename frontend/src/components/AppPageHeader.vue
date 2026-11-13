<template>
	<PageHeaderMobile v-if="isMobile">
		<PageHeaderMobileTitle :title="title" />
		<template #suffix><slot name="actions" /></template>
	</PageHeaderMobile>
	<PageHeader v-else>
		<PageHeaderTitle :title="title" />
		<div class="flex items-center gap-2"><slot name="actions" /></div>
	</PageHeader>
</template>

<script setup>
import { PageHeader, PageHeaderMobile, PageHeaderMobileTitle, PageHeaderTitle } from "frappe-ui";
import { useIsMobile } from "@/composables/useIsMobile";

defineProps({ title: { type: String, required: true } });
const isMobile = useIsMobile();
</script>
