<template>
	<div class="flex flex-col gap-2">
		<p v-if="error" role="alert" class="text-sm text-ink-red-4">{{ error }}</p>
		<p v-if="!rows.length" class="text-base text-ink-gray-5">{{ empty }}</p>
		<div
			v-for="(row, index) in rows"
			:key="index"
			class="grid grid-cols-[1fr_7rem_auto] items-start gap-2"
		>
			<Combobox
				v-model="row.obligation_template"
				:options="returnOptions"
				placeholder="Choose a return"
				:aria-label="`Return ${index + 1}`"
			/>
			<FormControl
				v-model="row.amount"
				type="number"
				placeholder="Fee"
				:aria-label="`Fee for ${row.obligation_template || `return ${index + 1}`}`"
			/>
			<Button
				variant="ghost"
				icon="lucide-x"
				:aria-label="`Remove ${row.obligation_template || `return ${index + 1}`}`"
				@click="rows.splice(index, 1)"
			/>
		</div>
		<p v-if="problem" role="alert" class="text-sm text-ink-red-4">{{ problem }}</p>
		<div>
			<Button
				icon-left="lucide-plus"
				label="Add a price"
				@click="rows.push({ obligation_template: '', amount: '' })"
			/>
		</div>
	</div>
</template>

<script setup>
// A price per return: each row a return from the obligation library and its fee. Used for the
// firm's prices (Settings → Billing) and a client's own.
import { computed, onMounted, ref } from "vue";
import { Button, Combobox, FormControl } from "frappe-ui";
import { getList } from "@/api";
import { pricesProblem } from "@/lib/billing";
import { returnGroups } from "@/lib/filings";
import { notLoaded } from "@/offline/reachability";

defineProps({ empty: { type: String, default: "No prices yet." } });
const rows = defineModel({ type: Array, required: true });

const templates = ref([]);
const error = ref("");
const returnOptions = computed(() => returnGroups(templates.value));
const problem = computed(() => pricesProblem(rows.value));

onMounted(async () => {
	try {
		templates.value = (
			await getList("Compliance Obligation Template", {
				fields: ["name", "law", "form"],
				filters: [["is_active", "=", 1]],
				orderBy: "name asc",
				limit: 1000,
			})
		).rows;
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("the obligation library") : err.message;
	}
});
</script>
