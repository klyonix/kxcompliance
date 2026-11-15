<template>
	<section class="flex flex-col gap-4" aria-labelledby="prices-heading">
		<div class="flex flex-col gap-0.5">
			<h2 id="prices-heading" class="text-base font-semibold text-ink-gray-8">
				Price per return
			</h2>
			<p class="text-sm text-ink-gray-5">
				What the firm charges for filing each return. A client's own price, set on the
				client, takes its place. Returns with no price are not billed.
			</p>
		</div>
		<PriceList
			v-model="prices"
			empty="No prices yet: filings are not billed until a return has one."
		/>
		<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
			<p v-if="error" role="alert" class="text-sm text-ink-red-4 sm:mr-auto">{{ error }}</p>
			<Button
				variant="solid"
				label="Save prices"
				:loading="saving"
				:disabled="Boolean(pricesProblem(prices))"
				@click="save"
			/>
		</div>
	</section>
</template>

<script setup>
// Billing settings, the Rate cards tab: the firm's price for filing each return.
import { ref, watch } from "vue";
import { Button, toast } from "frappe-ui";
import { call } from "@/api";
import PriceList from "@/components/PriceList.vue";
import { pricesProblem, pricesToSend } from "@/lib/billing";

const props = defineProps({ setup: { type: Object, required: true } });

const prices = ref([]);
const error = ref("");
const saving = ref(false);

watch(
	() => props.setup,
	(state) => {
		prices.value = (state.return_fees || []).map((row) => ({ ...row }));
	},
	{ immediate: true }
);

async function save() {
	error.value = "";
	saving.value = true;
	try {
		prices.value = await call(
			"kxcompliance.api.save_return_fees",
			{ fees: pricesToSend(prices.value) },
			{ httpMethod: "POST" }
		);
		toast.success("Prices saved");
	} catch (err) {
		error.value = err.message;
	} finally {
		saving.value = false;
	}
}
</script>
