<template>
	<section class="flex flex-col gap-4" aria-labelledby="billing-heading">
		<div class="flex flex-col gap-0.5">
			<h2 id="billing-heading" class="text-base font-semibold text-ink-gray-8">
				Billing your clients
			</h2>
			<p class="text-sm text-ink-gray-5">
				Bills are ERPNext invoices from the firm's own company, which is kept out of the
				compliance lists. GST is charged by state: CGST and SGST within the firm's state,
				IGST outside it.
			</p>
		</div>

		<p v-if="error" role="alert" class="text-base text-ink-red-4">{{ error }}</p>
		<Skeleton v-else-if="!setup" class="h-40 w-full rounded-lg" />

		<template v-else>
			<p
				v-if="setup.company"
				class="flex items-center gap-2 rounded-lg bg-surface-green-1 px-3 py-2 text-base text-ink-green-4"
			>
				<span class="lucide-circle-check size-4 shrink-0" aria-hidden="true" />
				Bills go out from {{ setup.company }}.
			</p>
			<p
				v-else-if="!setup.can_create_company"
				class="rounded-lg bg-surface-amber-1 px-3 py-2 text-base text-ink-amber-4"
			>
				Setting billing up makes the firm's own company in ERPNext, which needs a System
				Manager. Ask one to open this page, or to give you rights to create companies.
			</p>
			<FormControl
				v-if="!setup.company"
				v-model="name"
				label="Firm's name on its bills"
				placeholder="Rao & Associates"
				required
			/>
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
				<FormControl
					v-model="form.billing_gstin"
					label="Firm's GSTIN"
					placeholder="29AAACA1234F1Z5"
					description="Its state is read from it."
				/>
				<FormControl
					v-model="form.billing_state"
					type="select"
					label="Firm's state"
					description="Only when the firm has no GSTIN."
					:disabled="Boolean(form.billing_gstin.trim())"
					:options="[
						{ label: 'Choose', value: '' },
						...setup.states.map((state) => ({ label: state, value: state })),
					]"
				/>
			</div>
			<FormControl
				v-model="form.billing_address"
				type="textarea"
				label="Address on bills"
				:rows="3"
			/>
			<FormControl
				v-model="form.bank_details"
				type="textarea"
				label="Bank details on bills"
				placeholder="Bank, account number, IFSC, UPI ID"
				:rows="3"
			/>
			<FormControl
				v-model="form.bill_prefix"
				class="sm:w-56"
				label="Bill number prefix"
				placeholder="RA"
				description="Bills are numbered RA/26-27/0001 and on."
			/>
			<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
				<p v-if="saveError" role="alert" class="text-sm text-ink-red-4 sm:mr-auto">
					{{ saveError }}
				</p>
				<Button
					variant="solid"
					:label="setup.company ? 'Save billing details' : 'Set up billing'"
					:loading="saving"
					:disabled="!setup.company && !setup.can_create_company"
					@click="save"
				/>
			</div>
		</template>
	</section>

	<section v-if="setup?.company" class="flex flex-col gap-4" aria-labelledby="prices-heading">
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
			<p v-if="pricesError" role="alert" class="text-sm text-ink-red-4 sm:mr-auto">
				{{ pricesError }}
			</p>
			<Button
				variant="solid"
				label="Save prices"
				:loading="savingPrices"
				:disabled="Boolean(pricesProblem(prices))"
				@click="savePrices"
			/>
		</div>
	</section>
</template>

<script setup>
// Settings → Billing: the firm's own company, made once, and its details on every bill.
import { onMounted, reactive, ref } from "vue";
import { Button, FormControl, Skeleton, toast } from "frappe-ui";
import { call } from "@/api";
import PriceList from "@/components/PriceList.vue";
import { pricesProblem, pricesToSend } from "@/lib/billing";

const FIELDS = [
	"billing_gstin",
	"billing_state",
	"billing_address",
	"bank_details",
	"bill_prefix",
];

const setup = ref(null);
const form = reactive(Object.fromEntries(FIELDS.map((field) => [field, ""])));
const name = ref("");
const error = ref("");
const saveError = ref("");
const saving = ref(false);
const prices = ref([]);
const pricesError = ref("");
const savingPrices = ref(false);

async function savePrices() {
	pricesError.value = "";
	savingPrices.value = true;
	try {
		prices.value = await call(
			"kxcompliance.api.save_return_fees",
			{ fees: pricesToSend(prices.value) },
			{ httpMethod: "POST" }
		);
		toast.success("Prices saved");
	} catch (err) {
		pricesError.value = err.message;
	} finally {
		savingPrices.value = false;
	}
}

function fill(state) {
	setup.value = state;
	prices.value = (state.return_fees || []).map((row) => ({ ...row }));
	for (const field of FIELDS) form[field] = state[field] || "";
}

async function save() {
	saveError.value = "";
	saving.value = true;
	try {
		const details = Object.fromEntries(FIELDS.map((field) => [field, form[field].trim()]));
		const first = !setup.value.company;
		fill(
			await call(
				"kxcompliance.api.set_up_billing",
				{ details, ...(first ? { name: name.value.trim() } : {}) },
				{ httpMethod: "POST" }
			)
		);
		toast.success(first ? "Billing is set up" : "Billing details saved");
	} catch (err) {
		saveError.value = err.isNetwork
			? "This needs a connection to the server. Try again when you are back online."
			: err.message;
	} finally {
		saving.value = false;
	}
}

onMounted(async () => {
	try {
		fill(await call("kxcompliance.api.billing_setup"));
	} catch (err) {
		error.value = err.message;
	}
});
</script>
