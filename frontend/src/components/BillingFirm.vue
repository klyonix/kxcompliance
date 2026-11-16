<template>
	<section class="flex flex-col gap-4" aria-labelledby="firm-heading">
		<div class="flex flex-col gap-0.5">
			<h2 id="firm-heading" class="text-base font-semibold text-ink-gray-8">
				The firm on its bills
			</h2>
			<p class="text-sm text-ink-gray-5">
				Bills are ERPNext invoices from the firm's own company, kept out of the compliance
				lists.
			</p>
		</div>

		<p
			v-if="setup.company"
			class="flex items-center gap-2 rounded-lg bg-surface-green-1 px-3 py-2 text-base text-ink-green-4"
		>
			<span class="lucide-circle-check size-4 shrink-0" aria-hidden="true" />
			Bills go out from {{ setup.company }}.
		</p>
		<p
			v-else-if="!setup.can_create_company && !setup.suggested_name"
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
			:description="
				setup.suggested_name && name.trim() === setup.suggested_name
					? 'This company is already in ERPNext; bills go out from it.'
					: ''
			"
			required
		/>

		<LogoField
			v-model="form.billing_logo"
			label="Logo on bills and statements"
			alt="The firm's logo"
			:doctype="setup.settings_record.doctype"
			:docname="setup.settings_record.name"
		/>

		<div class="flex flex-col gap-1.5">
			<span class="text-xs text-ink-gray-5">GST status</span>
			<TabButtons
				v-model="form.gst_status"
				:options="setup.gst_statuses.map((status) => ({ label: status, value: status }))"
			/>
			<p class="text-sm text-ink-gray-5">{{ gstLine }}</p>
		</div>
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<FormControl
				v-model="form.billing_gstin"
				label="Firm's GSTIN"
				placeholder="29AAACA1234F1Z5"
				:description="
					form.gst_status === 'Not registered'
						? 'None, as the firm is not registered.'
						: 'Its state is read from it.'
				"
				:disabled="form.gst_status === 'Not registered'"
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
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<FormControl
				v-model="form.bank_details"
				type="textarea"
				label="Bank details on bills"
				placeholder="Bank, account number, IFSC"
				:rows="3"
			/>
			<FormControl
				v-model="form.upi_id"
				label="UPI ID"
				placeholder="raoassociates@okhdfc"
				description="Bills carry a QR code to pay the amount due by UPI."
			/>
		</div>
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<FormControl
				v-model="form.bill_prefix"
				label="Bill number prefix"
				placeholder="RA"
				:description="`Bills are numbered ${billNumberExample(form.bill_prefix)} and on.`"
			/>
			<FormControl
				v-model="form.default_sac"
				label="Default SAC code"
				placeholder="998221"
				description="For bill lines whose rate has no SAC code of its own."
			/>
		</div>
		<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
			<p v-if="saveError" role="alert" class="text-sm text-ink-red-4 sm:mr-auto">
				{{ saveError }}
			</p>
			<Button
				variant="solid"
				:label="setup.company ? 'Save billing details' : 'Set up billing'"
				:loading="saving"
				:disabled="!setup.company && !setup.can_create_company && !setup.suggested_name"
				@click="save"
			/>
		</div>
	</section>
</template>

<script setup>
// Billing settings, the Firm tab: the firm's own company, made once, and how it appears on bills.
import { computed, reactive, ref, watch } from "vue";
import { Button, FormControl, TabButtons, toast } from "frappe-ui";
import { call } from "@/api";
import { billNumberExample } from "@/lib/billing";
import LogoField from "@/components/LogoField.vue";

const props = defineProps({ setup: { type: Object, required: true } });
const emit = defineEmits(["saved"]);

const FIELDS = [
	"gst_status",
	"billing_gstin",
	"billing_state",
	"billing_address",
	"bank_details",
	"upi_id",
	"bill_prefix",
	"default_sac",
	"billing_logo",
];
const GST_LINES = {
	Registered: "A tax invoice with GST: CGST and SGST within the firm's state, IGST outside it.",
	"Not registered": "An invoice with no GST, as the firm does not collect it.",
	Composition:
		"A bill of supply with no GST, as a composition taxable person may not collect it.",
};

const form = reactive(Object.fromEntries(FIELDS.map((field) => [field, ""])));
const name = ref("");
const saveError = ref("");
const saving = ref(false);

const gstLine = computed(() => GST_LINES[form.gst_status] || "");

watch(
	() => props.setup,
	(state) => {
		for (const field of FIELDS) form[field] = state[field] || "";
		if (!state.company && !name.value) name.value = state.suggested_name || "";
		form.gst_status = form.gst_status || "Registered";
	},
	{ immediate: true }
);
// A firm not registered has no GSTIN to keep.
watch(
	() => form.gst_status,
	(status) => {
		if (status === "Not registered") form.billing_gstin = "";
	}
);

async function save() {
	saveError.value = "";
	saving.value = true;
	try {
		const details = Object.fromEntries(
			FIELDS.map((field) => [field, String(form[field] || "").trim()])
		);
		const first = !props.setup.company;
		const state = await call(
			"kxcompliance.api.set_up_billing",
			{ details, ...(first ? { name: name.value.trim() } : {}) },
			{ httpMethod: "POST" }
		);
		toast.success(first ? "Billing is set up" : "Billing details saved");
		emit("saved", state);
	} catch (err) {
		saveError.value = err.isNetwork
			? "This needs a connection to the server. Try again when you are back online."
			: err.message;
	} finally {
		saving.value = false;
	}
}
</script>
