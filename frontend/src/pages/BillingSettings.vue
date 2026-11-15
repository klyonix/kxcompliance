<template>
	<AppPageHeader
		title="Billing settings"
		:parent="boot.mayBill ? { label: 'Billing', route: { name: 'Billing' } } : null"
	/>

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6 sm:px-6">
		<p v-if="error" role="alert" class="text-base text-ink-red-4">{{ error }}</p>
		<Skeleton v-else-if="!setup" class="h-64 w-full rounded-lg" />

		<Tabs v-else v-model="tab">
			<FormControl
				v-if="isMobile"
				v-model="tab"
				type="select"
				:options="tabOptions"
				aria-label="Show"
			/>
			<TabList v-else class="overflow-x-auto">
				<TabTrigger value="firm" label="Firm" icon-left="lucide-building" />
				<TabTrigger
					value="rates"
					label="Rate cards"
					icon-left="lucide-tags"
					:disabled="!setup.company"
				/>
			</TabList>
			<TabPanel value="firm" class="flex flex-col gap-8 pt-2 sm:pt-6">
				<BillingFirm :setup="setup" @saved="(state) => (setup = state)" />
			</TabPanel>
			<TabPanel v-if="setup.company" value="rates" class="flex flex-col gap-8 pt-2 sm:pt-6">
				<BillingPrices :setup="setup" />
			</TabPanel>
		</Tabs>
	</div>
</template>

<script setup>
// Billing's own settings, for a firm's managers: the firm on its bills, and its rates.
import { computed, onMounted, ref } from "vue";
import { FormControl, Skeleton, TabList, TabPanel, TabTrigger, Tabs } from "frappe-ui";
import { call } from "@/api";
import { boot } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import BillingFirm from "@/components/BillingFirm.vue";
import BillingPrices from "@/components/BillingPrices.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { useTabQuery } from "@/composables/useTabQuery";

const isMobile = useIsMobile();
const tab = useTabQuery(["firm", "rates"]);
const setup = ref(null);
const error = ref("");

const tabOptions = computed(() => [
	{ label: "Firm", value: "firm" },
	...(setup.value?.company ? [{ label: "Rate cards", value: "rates" }] : []),
]);

onMounted(async () => {
	try {
		setup.value = await call("kxcompliance.api.billing_setup");
	} catch (err) {
		error.value = err.message;
	}
});
</script>
