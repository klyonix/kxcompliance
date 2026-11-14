<template>
	<div v-if="filterOffered()" class="flex items-center gap-2">
		<FormControl
			type="select"
			class="min-w-0 flex-1 sm:w-56 sm:flex-none"
			:model-value="clientFilter.client"
			:options="options"
			:disabled="!clientFilter.loaded"
			aria-label="Show one client"
			@update:model-value="chooseClient"
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
// Pick a client to narrow the lists to; the choice carries over to every list on this device.
import { computed, onMounted } from "vue";
import { Button, FormControl } from "frappe-ui";
import { chooseClient, clientFilter, filterOffered, loadClients } from "@/stores/clientFilter";

const options = computed(() => [
	{ label: "All clients", value: "" },
	...clientFilter.clients.map((row) => ({ label: row.name, value: row.name })),
]);

onMounted(loadClients);
</script>
