<template>
	<AppPageHeader :title="name ? `Edit ${form.title || 'item'}` : 'New item'" :parent="parent" />

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-6 sm:px-6">
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<div v-else-if="!options" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton class="h-6 w-1/3 rounded" />
			<Skeleton class="h-40 w-full rounded-lg" />
		</div>

		<template v-else>
			<section class="flex flex-col gap-4" aria-labelledby="item-heading">
				<h2 id="item-heading" class="text-base font-semibold text-ink-gray-8">Item</h2>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<FormControl
						v-model="form.item_type"
						type="select"
						label="Type"
						:options="[{ label: 'Choose a type', value: '' }, ...typeOptions]"
						:disabled="Boolean(name)"
					/>
					<FormControl
						v-model="form.title"
						label="Title"
						placeholder="Trade Licence - Bengaluru office"
					/>
					<FormControl
						v-model="form.company"
						type="select"
						label="Company"
						:options="[{ label: 'Choose a company', value: '' }, ...companyOptions]"
					/>
					<FormControl
						v-if="isDsc"
						v-model="form.holder"
						type="select"
						label="Held by"
						:options="[{ label: 'Choose the signatory', value: '' }, ...signatories]"
					/>
					<FormControl v-model="form.reference_number" label="Reference number" />
					<FormControl
						v-model="form.issuing_authority"
						label="Issuing authority"
						placeholder="BBMP, Fire Department, insurer…"
					/>
					<FormControl
						v-model="form.state"
						type="select"
						label="State"
						:options="[{ label: 'None', value: '' }, ...choices(options.states)]"
					/>
				</div>
			</section>

			<section class="flex flex-col gap-4" aria-labelledby="validity-heading">
				<h2 id="validity-heading" class="text-base font-semibold text-ink-gray-8">
					Validity
				</h2>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
					<FormControl
						v-model="form.issue_date"
						type="date"
						:format="pickerFormat()"
						label="Issued on"
					/>
					<FormControl
						v-model="form.valid_from"
						type="date"
						:format="pickerFormat()"
						label="Valid from"
					/>
					<FormControl
						v-model="form.valid_until"
						type="date"
						:format="pickerFormat()"
						:label="
							type?.renewal_cycle_months ? 'Valid until (needed)' : 'Valid until'
						"
					/>
				</div>
			</section>

			<section v-if="isDsc" class="flex flex-col gap-4" aria-labelledby="dsc-heading">
				<h2 id="dsc-heading" class="text-base font-semibold text-ink-gray-8">
					Digital signature
				</h2>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<FormControl
						v-model="form.dsc_class"
						type="select"
						label="Class"
						:options="choices(['', 'Class 3', 'DGFT'])"
					/>
					<FormControl
						v-model="form.dsc_purpose"
						type="select"
						label="Purpose"
						:options="choices(['', 'Signing', 'Encryption', 'Signing and Encryption'])"
					/>
					<FormControl
						v-model="form.certifying_authority"
						label="Certifying authority"
						placeholder="eMudhra, Capricorn…"
					/>
					<FormControl v-model="form.token_serial" label="Token serial number" />
				</div>
			</section>

			<section
				v-if="type?.category === 'Subscription' || type?.category === 'Contract'"
				class="flex flex-col gap-4"
				aria-labelledby="billing-heading"
			>
				<h2 id="billing-heading" class="text-base font-semibold text-ink-gray-8">
					Billing
				</h2>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
					<FormControl
						v-model="form.billing_cycle"
						type="select"
						label="Billed"
						:options="[
							{ label: 'Not set', value: '' },
							...choices(options.billing_cycles),
						]"
					/>
					<FormControl
						v-model="form.cancellation_notice_days"
						type="number"
						label="Notice to cancel (days)"
					/>
					<FormControl
						v-model="form.auto_renews"
						type="checkbox"
						label="Renews by itself"
					/>
				</div>
			</section>

			<section
				v-if="type?.category === 'Insurance'"
				class="flex flex-col gap-4"
				aria-labelledby="insurance-heading"
			>
				<h2 id="insurance-heading" class="text-base font-semibold text-ink-gray-8">
					Insurance
				</h2>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<FormControl v-model="form.sum_insured" type="number" label="Sum insured" />
					<FormControl v-model="form.premium" type="number" label="Premium" />
				</div>
			</section>

			<section class="flex flex-col gap-4" aria-labelledby="people-heading">
				<h2 id="people-heading" class="text-base font-semibold text-ink-gray-8">
					People and cost
				</h2>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
					<FormControl
						v-model="form.responsible"
						type="select"
						label="Responsible"
						:options="[{ label: 'Choose someone', value: '' }, ...people]"
					/>
					<FormControl
						v-model="form.reviewer"
						type="select"
						label="Reviewer"
						:options="[{ label: 'No reviewer', value: '' }, ...people]"
					/>
					<FormControl v-model="form.cost" type="number" label="Cost" />
				</div>
				<FormControl v-model="form.notes" type="textarea" label="Notes" :rows="3" />
			</section>
		</template>
	</div>

	<div
		v-if="options"
		class="sticky bottom-0 z-10 mt-auto border-t border-outline-gray-1 bg-surface-base"
	>
		<div
			class="mx-auto flex w-full max-w-3xl flex-col-reverse gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-end sm:px-6"
		>
			<p v-if="saveError" role="alert" class="text-sm text-ink-red-4 sm:mr-auto">
				{{ saveError }}
			</p>
			<Button
				variant="solid"
				:label="name ? 'Save' : 'Add to the register'"
				:loading="saving"
				@click="save"
			/>
		</div>
	</div>
</template>

<script setup>
// Add a register item (licence, registration, certificate, insurance, subscription, DSC), or
// change one; the type decides which details it asks for.
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { Button, FormControl, Skeleton, toast } from "frappe-ui";
import { call, createDoc, getDoc, updateDoc } from "@/api";
import { boot } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { pickerFormat } from "@/lib/format";
import { DSC_TYPE } from "@/lib/items";
import { personOptions } from "@/lib/people";
import { notLoaded } from "@/offline/reachability";

const props = defineProps({ name: { type: String, default: "" } });

// The fields the form sends; the rest of an item is kept as it is.
const FIELDS = [
	"title",
	"item_type",
	"company",
	"reference_number",
	"issuing_authority",
	"state",
	"issue_date",
	"valid_from",
	"valid_until",
	"dsc_class",
	"dsc_purpose",
	"certifying_authority",
	"token_serial",
	"billing_cycle",
	"cancellation_notice_days",
	"auto_renews",
	"sum_insured",
	"premium",
	"responsible",
	"reviewer",
	"cost",
	"notes",
];

const router = useRouter();
const options = ref(null);
const signatoryRows = ref([]);
const error = ref("");
const saveError = ref("");
const saving = ref(false);
const form = reactive({
	...Object.fromEntries(FIELDS.map((field) => [field, ""])),
	holder: "",
	auto_renews: false,
	company: boot.defaultCompany || "",
	responsible: boot.user,
});

const parent = computed(() =>
	props.name
		? {
				label: form.title || "Item",
				route: { name: "ComplianceItem", params: { name: props.name } },
		  }
		: { label: "Register", route: { name: "Register" } }
);
const choices = (values) => values.map((value) => ({ label: value || "Not set", value }));
const type = computed(() => options.value?.item_types.find((row) => row.name === form.item_type));
const typeOptions = computed(() =>
	options.value.item_types.map((row) => ({
		label: `${row.name} (${row.category})`,
		value: row.name,
	}))
);
const companyOptions = boot.companies.map((company) => ({ label: company, value: company }));
const people = computed(() => personOptions(options.value?.people || []));
const isDsc = computed(() => form.item_type === DSC_TYPE);
const signatories = computed(() =>
	signatoryRows.value.map(([value, label, designation]) => ({
		label: designation ? `${label} (${designation})` : label,
		value,
	}))
);

// The signatories who sign for the chosen company, for a DSC's holder.
async function loadSignatories() {
	if (!isDsc.value || !form.company) {
		signatoryRows.value = [];
		return;
	}
	signatoryRows.value = await call(
		"compliance_plus.compliance_plus.doctype.signatory.signatory.signatories_for",
		{
			doctype: "Signatory",
			txt: "",
			searchfield: "full_name",
			start: 0,
			page_len: 50,
			filters: { company: form.company },
		}
	);
}

function values() {
	const result = Object.fromEntries(
		FIELDS.map((field) => [field, form[field] === "" ? null : form[field]])
	);
	result.auto_renews = form.auto_renews ? 1 : 0;
	if (isDsc.value)
		Object.assign(result, { holder_type: "Signatory", holder: form.holder || null });
	return result;
}

async function save() {
	saveError.value = "";
	if (!form.item_type || !form.title.trim() || !form.company) {
		saveError.value = "Choose the type and company, and give the item a title.";
		return;
	}
	saving.value = true;
	try {
		const saved = props.name
			? await updateDoc("Compliance Item", props.name, values())
			: await createDoc("Compliance Item", { holder_type: "Company", ...values() });
		toast.success(props.name ? "Item saved" : "Added to the register");
		router.replace({ name: "ComplianceItem", params: { name: saved.name } });
	} catch (err) {
		saveError.value = err.isNetwork
			? "The item did not reach the server. Try again when you are back online."
			: err.message;
	} finally {
		saving.value = false;
	}
}

watch(() => [form.item_type, form.company], loadSignatories);

onMounted(async () => {
	try {
		options.value = await call("compliance_plus.api.item_form_options");
		if (props.name) {
			const item = await getDoc("Compliance Item", props.name);
			for (const field of FIELDS) form[field] = item[field] ?? "";
			form.auto_renews = Boolean(item.auto_renews);
			form.holder = item.holder_type === "Signatory" ? item.holder : "";
		}
		await loadSignatories();
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this item", "opened") : err.message;
	}
});
</script>
