<template>
	<AppPageHeader title="New bill" :parent="parent" />

	<form
		class="mx-auto flex w-full max-w-2xl flex-col gap-6 px-4 py-6 sm:px-6"
		novalidate
		@submit.prevent="save"
	>
		<p class="text-base text-ink-gray-6">
			A draft bill for one of a client's companies, from the returns filed for it, the
			client's recurring charges, services and anything else. GST is added by the company's
			state. Check it on its page, then send it.
		</p>
		<p v-if="error" role="alert" class="text-base text-ink-red-4">{{ error }}</p>

		<FormControl
			v-if="!fromClient"
			v-model="client"
			type="select"
			label="Client"
			:options="[
				{ label: 'Choose a client', value: '' },
				...clients.map((name) => ({ label: name, value: name })),
			]"
		/>

		<FormControl
			v-if="options && options.companies.length > 1"
			:model-value="options.company"
			type="select"
			label="Company billed"
			:options="options.companies.map((name) => ({ label: name, value: name }))"
			:description="
				options.company === options.recurring_company
					? 'This company carries the client\'s recurring charges.'
					: `The client's recurring charges go on ${options.recurring_company}'s bills.`
			"
			@update:model-value="chooseCompany"
		/>

		<Skeleton v-if="client && !options && !error" class="h-40 w-full rounded-lg" />

		<template v-else-if="options">
			<section class="flex flex-col gap-2" aria-labelledby="filed-heading">
				<h2 id="filed-heading" class="text-base font-semibold text-ink-gray-8">
					Returns filed, not billed yet
				</h2>
				<p v-if="!options.filings.length" class="text-base text-ink-gray-5">
					None: every priced return filed for {{ options.company || client }} is billed
					or on a draft.
				</p>
				<label
					v-for="filing in options.filings"
					:key="filing.name"
					class="flex items-start gap-3 border-b border-outline-gray-1 py-2 last:border-b-0"
				>
					<input
						v-model="ticked"
						type="checkbox"
						:value="filing.name"
						class="mt-1 rounded border-outline-gray-3"
					/>
					<span class="flex min-w-0 flex-1 flex-col">
						<span class="text-base text-ink-gray-8"
							>{{ filing.obligation_template }}, {{ filing.period_label }}</span
						>
						<span class="truncate text-sm text-ink-gray-5">{{ filing.company }}</span>
					</span>
					<span class="text-base text-ink-gray-8">{{ money(filing.fee) }}</span>
				</label>
			</section>

			<label
				v-if="options.recurring.length"
				class="flex items-start gap-3 rounded-lg bg-surface-gray-1 px-3 py-2.5"
			>
				<input
					v-model="withRecurring"
					type="checkbox"
					class="mt-1 rounded border-outline-gray-3"
				/>
				<span class="flex flex-1 flex-col gap-1">
					<span class="text-base font-medium text-ink-gray-8"
						>Recurring charges due</span
					>
					<span
						v-for="charge in options.recurring"
						:key="charge.description"
						class="flex justify-between gap-3 text-base text-ink-gray-7"
					>
						<span>{{ charge.description }}</span>
						<span>{{ money(charge.amount) }}</span>
					</span>
				</span>
			</label>

			<section
				v-if="options.services.length"
				class="flex flex-col gap-2"
				aria-labelledby="services-heading"
			>
				<h2 id="services-heading" class="text-base font-semibold text-ink-gray-8">
					Services done
				</h2>
				<div
					v-for="(row, index) in services"
					:key="index"
					class="grid grid-cols-[1fr_6rem_auto] items-start gap-2"
				>
					<FormControl
						v-model="row.service"
						type="select"
						:aria-label="`Service ${index + 1}`"
						:options="[
							{ label: 'Choose a service', value: '' },
							...options.services.map((rate) => ({
								label: `${rate.service} (${money(
									rate.amount
								)} ${rate.unit.toLowerCase()})`,
								value: rate.service,
							})),
						]"
					/>
					<FormControl
						v-model="row.qty"
						type="number"
						:placeholder="unitOf(row.service) === 'Per hour' ? 'Hours' : 'How many'"
						:aria-label="`How many of service ${index + 1}`"
					/>
					<Button
						variant="ghost"
						icon="lucide-x"
						:aria-label="`Remove service ${index + 1}`"
						@click="services.splice(index, 1)"
					/>
				</div>
				<div>
					<Button
						icon-left="lucide-plus"
						label="Add a service"
						@click="services.push({ service: '', qty: '' })"
					/>
				</div>
			</section>

			<section class="flex flex-col gap-2" aria-labelledby="other-heading">
				<h2 id="other-heading" class="text-base font-semibold text-ink-gray-8">
					Other lines
				</h2>
				<div
					v-for="(line, index) in lines"
					:key="index"
					class="grid grid-cols-[1fr_7rem_auto] items-start gap-2 sm:grid-cols-[1fr_7rem_auto_auto]"
				>
					<FormControl
						v-model="line.description"
						placeholder="What it is for"
						:aria-label="`Line ${index + 1}`"
					/>
					<FormControl
						v-model="line.amount"
						type="number"
						placeholder="Amount"
						:aria-label="`Amount of line ${index + 1}`"
					/>
					<Button
						variant="ghost"
						icon="lucide-x"
						:aria-label="`Remove line ${index + 1}`"
						class="sm:order-last"
						@click="lines.splice(index, 1)"
					/>
					<FormControl
						v-model="line.government"
						class="col-span-3 sm:col-span-1 sm:self-center"
						type="checkbox"
						label="Government fee, no GST"
					/>
				</div>
				<div>
					<Button
						icon-left="lucide-plus"
						label="Add a line"
						@click="lines.push({ description: '', amount: '', government: false })"
					/>
				</div>
			</section>

			<p class="text-base text-ink-gray-7">{{ money(subtotal) }} before GST.</p>
			<p v-if="formError" role="alert" class="text-base text-ink-red-4">{{ formError }}</p>

			<div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
				<Button label="Cancel" :route="parent.route" :disabled="saving" />
				<Button
					type="submit"
					variant="solid"
					label="Make the draft"
					:loading="saving"
					:disabled="!subtotal"
				/>
			</div>
		</template>
	</form>
</template>

<script setup>
// A new draft bill for one client, opened from its page or with a client to choose.
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button, FormControl, Skeleton, toast } from "frappe-ui";
import { call } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { billSubtotal, linesProblem, linesToSend, money, servicesProblem } from "@/lib/billing";

const route = useRoute();
const router = useRouter();

const fromClient = Boolean(route.query.client);
const client = ref(String(route.query.client || ""));
const clients = ref([]);
const options = ref(null);
const ticked = ref([]);
const withRecurring = ref(false);
const services = ref([]);
const lines = ref([]);
const error = ref("");
const formError = ref("");
const saving = ref(false);

const parent = computed(() =>
	fromClient
		? { label: client.value, route: { name: "Client", params: { name: client.value } } }
		: { label: "Clients", route: { name: "Clients" } }
);
const subtotal = computed(() =>
	options.value
		? billSubtotal({
				filings: options.value.filings,
				ticked: ticked.value,
				recurring: options.value.recurring,
				withRecurring: withRecurring.value,
				services: services.value,
				rates: options.value.services,
				lines: lines.value,
		  })
		: 0
);

async function loadOptions(company = route.query.company || null) {
	options.value = null;
	error.value = "";
	if (!client.value) return;
	try {
		options.value = await call("kxcompliance.api.bill_options", {
			client: client.value,
			// Left out until one is chosen: the server starts with the client's first company.
			...(company ? { company } : {}),
		});
		// Everything there is to bill starts ticked; the person unticks what waits.
		ticked.value = options.value.filings.map((filing) => filing.name);
		withRecurring.value = options.value.recurring.length > 0;
		services.value = [];
	} catch (err) {
		error.value = err.message;
	}
}

// Another company: what may be billed is that company's.
const chooseCompany = (company) => loadOptions(company);

const unitOf = (service) => options.value?.services.find((rate) => rate.service === service)?.unit;

async function save() {
	formError.value = servicesProblem(services.value) || linesProblem(lines.value) || "";
	if (formError.value) return;
	saving.value = true;
	try {
		const { name } = await call(
			"kxcompliance.api.create_bill",
			{
				client: client.value,
				company: options.value.company,
				filings: ticked.value,
				recurring: withRecurring.value,
				services: services.value.map((row) => ({
					service: row.service,
					qty: Number(row.qty),
				})),
				lines: linesToSend(lines.value),
			},
			{ httpMethod: "POST" }
		);
		toast.success("Draft bill made");
		router.replace({ name: "Bill", params: { name } });
	} catch (err) {
		formError.value = err.message;
	} finally {
		saving.value = false;
	}
}

watch(client, () => loadOptions());
onMounted(async () => {
	if (!fromClient) {
		clients.value = (await call("kxcompliance.api.client_choices").catch(() => [])).map(
			(row) => row.name
		);
	}
	loadOptions();
});
</script>
