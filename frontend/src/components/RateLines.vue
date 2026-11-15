<template>
	<div class="flex flex-col gap-2">
		<p v-if="error" role="alert" class="text-sm text-ink-red-4">{{ error }}</p>
		<p v-if="!rows.length" class="text-base text-ink-gray-5">{{ empty }}</p>
		<div
			v-if="rows.length"
			class="hidden grid-cols-[1fr_9rem_7rem_6rem_2rem] gap-2 px-1 text-xs font-medium text-ink-gray-5 sm:grid"
			aria-hidden="true"
		>
			<span>Return or service</span>
			<span>Charged</span>
			<span>Rate</span>
			<span>SAC code</span>
			<span />
		</div>
		<div
			v-for="(row, index) in rows"
			:key="index"
			class="grid grid-cols-2 items-start gap-2 border-b border-outline-gray-1 pb-2 sm:grid-cols-[1fr_9rem_7rem_6rem_2rem] sm:border-0 sm:pb-0"
		>
			<div class="col-span-2 sm:col-span-1">
				<Combobox
					v-if="row.kind === 'Return'"
					v-model="row.obligation_template"
					:options="returnOptions"
					placeholder="Choose a return"
					:aria-label="`Return ${index + 1}`"
				/>
				<FormControl
					v-else
					v-model="row.service"
					placeholder="Service, such as Advisory or Retainer"
					:aria-label="`Service ${index + 1}`"
				/>
			</div>
			<FormControl
				v-model="row.unit"
				type="select"
				:aria-label="`How ${nameOf(row, index)} is charged`"
				:options="
					(row.kind === 'Return' ? RETURN_UNITS : SERVICE_UNITS).map((unit) => ({
						label: unit,
						value: unit,
					}))
				"
			/>
			<FormControl
				v-model="row.amount"
				type="number"
				placeholder="Rate"
				:aria-label="`Rate for ${nameOf(row, index)}`"
			/>
			<FormControl
				v-model="row.sac_code"
				placeholder="SAC"
				:aria-label="`SAC code for ${nameOf(row, index)}`"
			/>
			<Button
				variant="ghost"
				icon="lucide-x"
				:aria-label="`Remove ${nameOf(row, index)}`"
				@click="rows.splice(index, 1)"
			/>
		</div>
		<p v-if="problem" role="alert" class="text-sm text-ink-red-4">{{ problem }}</p>
		<div class="flex flex-wrap gap-2">
			<Button
				icon-left="lucide-plus"
				label="Add a return"
				@click="rows.push(newRate('Return'))"
			/>
			<Button
				icon-left="lucide-plus"
				label="Add a service"
				@click="rows.push(newRate('Service'))"
			/>
		</div>
	</div>
</template>

<script setup>
// Rate lines: each prices a return per filing, or a service by the hour or item or every month,
// quarter or year, with the SAC code printed on the bill. Used on rate cards and a client's own
// rates.
import { computed, onMounted, ref } from "vue";
import { Button, Combobox, FormControl } from "frappe-ui";
import { getList } from "@/api";
import { RETURN_UNITS, SERVICE_UNITS, newRate, ratesProblem } from "@/lib/billing";
import { returnGroups } from "@/lib/filings";
import { notLoaded } from "@/offline/reachability";

defineProps({ empty: { type: String, default: "No rates yet." } });
const rows = defineModel({ type: Array, required: true });

const templates = ref([]);
const error = ref("");
const returnOptions = computed(() => returnGroups(templates.value));
const problem = computed(() => ratesProblem(rows.value));

const nameOf = (row, index) =>
	(row.kind === "Return" ? row.obligation_template : row.service) || `rate ${index + 1}`;

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
