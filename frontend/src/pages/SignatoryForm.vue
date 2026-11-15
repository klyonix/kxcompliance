<template>
	<AppPageHeader
		:title="name ? form.full_name || 'Signatory' : 'New signatory'"
		:parent="{ label: 'Signatories', route: { name: 'Signatories' } }"
	/>

	<RecordFrame doctype="Signatory" :name="name" :facts="name && ready ? keyFacts : []">
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<div v-else-if="!ready" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton class="h-6 w-1/3 rounded" />
			<Skeleton class="h-40 w-full rounded-lg" />
		</div>

		<template v-else>
			<section class="flex flex-col gap-4" aria-labelledby="person-heading">
				<h2 id="person-heading" class="text-base font-semibold text-ink-gray-8">Person</h2>
				<FormControl
					v-model="form.full_name"
					label="Full name"
					:disabled="!editable"
					:error="checking && !form.full_name.trim() ? 'Give the person\'s name' : ''"
				/>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<FormControl
						v-model="form.company"
						type="select"
						label="Signs for"
						:options="companyOptions"
						:disabled="!editable"
						:error="checking && !form.company ? 'Choose the company' : ''"
					/>
					<FormControl
						v-model="form.designation"
						type="select"
						label="Designation"
						:options="designationOptions"
						:disabled="!editable"
					/>
					<FormControl
						v-model="form.din"
						label="DIN / DPIN"
						placeholder="8 digits"
						:disabled="!editable"
					/>
					<FormControl
						v-model="form.pan"
						label="PAN"
						placeholder="ABCDE1234F"
						:disabled="!editable || panMasked"
						:description="panMasked ? MASKED_NOTE : undefined"
					/>
					<FormControl
						v-model="form.email"
						type="email"
						label="Email"
						:disabled="!editable"
					/>
					<FormControl
						v-model="form.mobile"
						label="Mobile"
						:disabled="!editable || mobileMasked"
						:description="mobileMasked ? MASKED_NOTE : undefined"
					/>
				</div>
				<FormControl
					v-model="form.is_active"
					type="checkbox"
					label="Still signs (untick when the person resigns or retires)"
					:disabled="!editable"
				/>
			</section>

			<section class="flex flex-col gap-3" aria-labelledby="companies-heading">
				<div class="flex flex-col gap-0.5">
					<h2 id="companies-heading" class="text-base font-semibold text-ink-gray-8">
						Also signs for
					</h2>
					<p class="text-sm text-ink-gray-5">
						A promoter often signs for several group companies with one DSC.
					</p>
				</div>
				<div
					v-for="(row, index) in form.other_companies"
					:key="index"
					class="flex flex-col gap-2 sm:flex-row sm:items-end"
				>
					<FormControl
						v-model="row.company"
						type="select"
						label="Company"
						:options="companyOptions"
						class="sm:flex-1"
						:disabled="!editable"
					/>
					<FormControl
						v-model="row.designation"
						type="select"
						label="Designation"
						:options="designationOptions"
						class="sm:flex-1"
						:disabled="!editable"
					/>
					<Button
						v-if="editable"
						variant="ghost"
						icon="lucide-trash-2"
						label="Remove company"
						@click="form.other_companies.splice(index, 1)"
					/>
				</div>
				<div v-if="editable">
					<Button
						icon-left="lucide-plus"
						label="Add a company"
						@click="form.other_companies.push({ company: '', designation: '' })"
					/>
				</div>
			</section>

			<section v-if="name" class="flex flex-col gap-1" aria-labelledby="dscs-heading">
				<h2 id="dscs-heading" class="pb-2 text-base font-semibold text-ink-gray-8">
					Digital signatures
				</h2>
				<p v-if="!dscs.length" class="text-base text-ink-gray-5">
					None recorded. Add a DSC in the Register with this person as its holder.
				</p>
				<WorkRow v-for="dsc in dscs" :key="dsc.name" :row="itemRow(dsc)" />
			</section>
		</template>
	</RecordFrame>

	<div
		v-if="ready && editable"
		class="sticky bottom-0 z-10 mt-auto border-t border-outline-gray-1 bg-surface-base"
	>
		<div
			class="mx-auto flex w-full flex-col-reverse gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-end sm:px-6"
			:class="recordWidth(name)"
		>
			<p v-if="saveError" role="alert" class="text-sm text-ink-red-4 sm:mr-auto">
				{{ saveError }}
			</p>
			<Button
				variant="solid"
				:label="name ? 'Save' : 'Add signatory'"
				:loading="saving"
				@click="save"
			/>
		</div>
	</div>
</template>

<script setup>
// A signatory: who they are, which companies they sign for, and the DSCs they hold.
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button, FormControl, Skeleton, toast } from "frappe-ui";
import { createDoc, getDoc, getList, updateDoc } from "@/api";
import { boot, mayRecord } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import RecordFrame from "@/components/RecordFrame.vue";
import WorkRow from "@/components/WorkRow.vue";
import { DSC_TYPE, ITEM_LIST_FIELDS, itemRow } from "@/lib/items";
import { isMasked } from "@/lib/privacy";
import { recordWidth } from "@/lib/records";
import { DESIGNATIONS } from "@/lib/signatories";
import { notLoaded } from "@/offline/reachability";

const props = defineProps({ name: { type: String, default: "" } });

const route = useRoute();
const router = useRouter();
const editable = mayRecord();
// The band across the top: who the person is for the company, and their digital signatures.
const keyFacts = computed(() => [
	{ label: "Designation", icon: "lucide-briefcase", value: form.designation },
	{ label: "Company", icon: "lucide-building-2", value: form.company },
	{ label: "DIN", icon: "lucide-hash", value: form.din },
	{
		label: "Digital signatures",
		icon: "lucide-key-round",
		value: String(dscs.value.length),
	},
]);
// PAN and mobile come masked to all but managers, who alone may see or change them.
const MASKED_NOTE = "Only managers see and change it in full.";
const loaded = reactive({ pan: "", mobile: "" });
const panMasked = computed(() => isMasked(loaded.pan));
const mobileMasked = computed(() => isMasked(loaded.mobile));
const ready = ref(false);
const error = ref("");
const saveError = ref("");
const saving = ref(false);
const checking = ref(false);
const dscs = ref([]);
const form = reactive({
	full_name: "",
	company: "",
	designation: "Director",
	din: "",
	pan: "",
	email: "",
	mobile: "",
	is_active: true,
	other_companies: [],
});

const companyOptions = computed(() => [
	{ label: "Choose a company", value: "" },
	...boot.companies.map((company) => ({ label: company, value: company })),
]);
const designationOptions = DESIGNATIONS.map((value) => ({ label: value, value }));

async function save() {
	checking.value = true;
	saveError.value = "";
	if (!form.full_name.trim() || !form.company) return;
	saving.value = true;
	const values = {
		full_name: form.full_name.trim(),
		company: form.company,
		designation: form.designation,
		din: form.din.trim(),
		email: form.email.trim() || null,
		// Masked values are left as they are; the server keeps the real ones anyway.
		...(panMasked.value ? {} : { pan: form.pan.trim() }),
		...(mobileMasked.value ? {} : { mobile: form.mobile.trim() || null }),
		is_active: form.is_active ? 1 : 0,
		other_companies: form.other_companies
			.filter((row) => row.company)
			.map((row) => ({ company: row.company, designation: row.designation || null })),
	};
	try {
		const saved = props.name
			? await updateDoc("Signatory", props.name, values)
			: await createDoc("Signatory", values);
		toast.success(props.name ? "Signatory saved" : "Signatory added");
		if (!props.name) router.replace({ name: "Signatory", params: { name: saved.name } });
	} catch (err) {
		saveError.value = err.isNetwork
			? "The signatory did not reach the server. Try again when you are back online."
			: err.message;
	} finally {
		saving.value = false;
	}
}

async function load() {
	ready.value = false;
	error.value = "";
	try {
		if (props.name) {
			const signatory = await getDoc("Signatory", props.name);
			loaded.pan = signatory.pan || "";
			loaded.mobile = signatory.mobile || "";
			Object.assign(form, {
				full_name: signatory.full_name,
				company: signatory.company,
				designation: signatory.designation || "",
				din: signatory.din || "",
				pan: signatory.pan || "",
				email: signatory.email || "",
				mobile: signatory.mobile || "",
				is_active: Boolean(signatory.is_active),
				other_companies: signatory.other_companies.map((row) => ({
					company: row.company,
					designation: row.designation || "",
				})),
			});
			dscs.value = (
				await getList("Compliance Item", {
					fields: [...ITEM_LIST_FIELDS, "company"],
					filters: [
						["item_type", "=", DSC_TYPE],
						["holder_type", "=", "Signatory"],
						["holder", "=", props.name],
					],
					orderBy: "valid_until desc",
					limit: 20,
				})
			).rows;
		} else if (boot.companies.includes(route.query.company)) {
			form.company = route.query.company;
		}
		ready.value = true;
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this signatory", "opened") : err.message;
	}
}

watch(() => props.name, load);
onMounted(load);
</script>
