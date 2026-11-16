<template>
	<div v-if="filterOffered()" class="flex items-center gap-2" data-tour="client-filter">
		<!-- Type part of a client's or company's name to find it among many. -->
		<Combobox
			class="min-w-0 flex-1 sm:w-72 sm:flex-none"
			v-model:query="query"
			:model-value="clientFilter.client || null"
			:options="options"
			:filterable="false"
			:disabled="!clientFilter.loaded"
			placeholder="All clients"
			aria-label="Show one client"
			@update:model-value="(value) => chooseClient(value || '')"
		/>
		<Button
			v-if="clientFilter.client"
			variant="ghost"
			icon="lucide-x"
			label="Show all clients"
			@click="chooseClient('')"
		/>
	</div>
	<div
		v-else-if="companyChoice && companyFilterOffered()"
		class="flex items-center gap-2"
		data-tour="company-filter"
	>
		<Combobox
			class="min-w-0 flex-1 sm:w-72 sm:flex-none"
			:model-value="chosenCompanies?.[0] || null"
			:options="boot.companies.map((name) => ({ label: name, value: name }))"
			placeholder="All companies"
			aria-label="Show one company"
			@update:model-value="(value) => chooseCompany(value || '')"
		/>
		<Button
			v-if="chosenCompanies"
			variant="ghost"
			icon="lucide-x"
			label="Show all companies"
			@click="chooseCompany('')"
		/>
	</div>
</template>

<script setup>
// Pick a client to narrow the app to; the choice carries over to every page on this device. With
// many clients, typing finds one by its name or by one of its companies. An organisation with
// more than one company picks a company here instead.
import { computed, onMounted, ref } from "vue";
import { Button, Combobox } from "frappe-ui";
import { boot } from "@/boot";
import { clientLabel } from "@/lib/clients";
import {
	chooseClient,
	chooseCompany,
	chosenCompanies,
	clientFilter,
	companyFilterOffered,
	filterOffered,
	loadClients,
} from "@/stores/clientFilter";

defineProps({
	// False where a company choice means nothing, such as the list of companies itself.
	companyChoice: { type: Boolean, default: true },
});

const query = ref("");
// Every word typed must be in the client's name or one of its companies, so a company's name
// finds its client.
const options = computed(() => {
	const words = query.value.toLowerCase().split(/\s+/).filter(Boolean);
	const chosen = clientFilter.clients.find((row) => row.name === clientFilter.client);
	// While the box shows the chosen client's own name, every client is offered.
	const searching = words.length && query.value !== clientLabel(chosen);
	return clientFilter.clients
		.filter((row) => {
			if (!searching) return true;
			const text = [clientLabel(row), ...(row.companies || [])].join(" ").toLowerCase();
			return words.every((word) => text.includes(word));
		})
		.map((row) => ({
			label: clientLabel(row),
			value: row.name,
			description: (row.companies || []).join(", "),
		}));
});

onMounted(loadClients);
</script>
