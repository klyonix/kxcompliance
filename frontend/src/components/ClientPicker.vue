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
</template>

<script setup>
// Pick a client to narrow the app to; the choice carries over to every page on this device. With
// many clients, typing finds one by its name or by one of its companies.
import { computed, onMounted, ref } from "vue";
import { Button, Combobox } from "frappe-ui";
import { chooseClient, clientFilter, filterOffered, loadClients } from "@/stores/clientFilter";

const query = ref("");
// Every word typed must be in the client's name or one of its companies, so a company's name
// finds its client.
const options = computed(() => {
	const words = query.value.toLowerCase().split(/\s+/).filter(Boolean);
	const chosen = clientFilter.clients.find((row) => row.name === clientFilter.client);
	// While the box shows the chosen client's own name, every client is offered.
	const searching = words.length && query.value !== chosen?.name;
	return clientFilter.clients
		.filter((row) => {
			if (!searching) return true;
			const text = [row.name, ...(row.companies || [])].join(" ").toLowerCase();
			return words.every((word) => text.includes(word));
		})
		.map((row) => ({
			label: row.name,
			value: row.name,
			description: (row.companies || []).join(", "),
		}));
});

onMounted(loadClients);
</script>
