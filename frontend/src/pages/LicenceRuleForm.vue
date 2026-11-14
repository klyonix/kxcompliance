<template>
	<AppPageHeader
		:title="name ? form.item_type || 'Licence rule' : 'New licence rule'"
		:parent="{ label: 'Licence rules', route: { name: 'LicenceRules' } }"
	/>

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-6 sm:px-6">
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<Skeleton v-else-if="!options" class="h-48 w-full rounded-lg" />

		<template v-else>
			<section class="flex flex-col gap-4" aria-labelledby="rule-heading">
				<h2 id="rule-heading" class="text-base font-semibold text-ink-gray-8">The rule</h2>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<FormControl
						v-model="form.item_type"
						type="select"
						label="Licence"
						:options="[
							{ label: 'Choose the licence', value: '' },
							...choices(options.item_types),
						]"
					/>
					<FormControl
						v-model="form.party_type"
						type="select"
						label="Who must hold it"
						:options="[
							{ label: 'Customers', value: 'Customer' },
							{ label: 'Suppliers', value: 'Supplier' },
						]"
					/>
					<FormControl
						v-model="form.action"
						type="select"
						label="When it is missing"
						:options="[
							{ label: 'Block the document', value: 'Block' },
							{ label: 'Only warn', value: 'Warn' },
						]"
					/>
					<FormControl
						v-model="form.grace_days"
						type="number"
						label="Still counts after expiry for (days)"
					/>
				</div>
				<FormControl v-model="form.is_active" type="checkbox" label="In use" />
			</section>

			<section class="flex flex-col gap-3" aria-labelledby="documents-heading">
				<div class="flex flex-col gap-0.5">
					<h2 id="documents-heading" class="text-base font-semibold text-ink-gray-8">
						Checked on
					</h2>
					<p class="text-sm text-ink-gray-5">
						The {{ form.party_type === "Supplier" ? "buying" : "selling" }} documents
						this rule is checked on when they are saved.
					</p>
				</div>
				<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
					<FormControl
						v-for="document in partyDocuments"
						:key="document.field"
						v-model="form[document.field]"
						type="checkbox"
						:label="document.doctype"
					/>
				</div>
			</section>

			<section class="flex flex-col gap-3" aria-labelledby="scope-heading">
				<div class="flex flex-col gap-0.5">
					<h2 id="scope-heading" class="text-base font-semibold text-ink-gray-8">
						Only for
					</h2>
					<p class="text-sm text-ink-gray-5">
						Leave a list empty for every item, or every
						{{ form.party_type === "Supplier" ? "supplier" : "customer" }}.
					</p>
				</div>
				<details class="rounded-lg border border-outline-gray-1 px-3 py-2">
					<summary class="cursor-pointer text-base text-ink-gray-8">
						Item groups
						<span class="text-ink-gray-5"
							>· {{ summary(form.item_groups, "every item") }}</span
						>
					</summary>
					<div class="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
						<FormControl
							v-for="group in options.item_groups"
							:key="group"
							v-model="form.item_groups[group]"
							type="checkbox"
							:label="group"
						/>
					</div>
				</details>
				<details class="rounded-lg border border-outline-gray-1 px-3 py-2">
					<summary class="cursor-pointer text-base text-ink-gray-8">
						{{ form.party_type === "Supplier" ? "Supplier" : "Customer" }} groups
						<span class="text-ink-gray-5"
							>· {{ summary(form.party_groups, "all of them") }}</span
						>
					</summary>
					<div class="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
						<FormControl
							v-for="group in partyGroups"
							:key="group"
							v-model="form.party_groups[group]"
							type="checkbox"
							:label="group"
						/>
					</div>
				</details>
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
				:label="name ? 'Save' : 'Add rule'"
				:loading="saving"
				@click="save"
			/>
		</div>
	</div>
</template>

<script setup>
// A licence rule: which licence, who must hold it, block or warn, the documents it is checked on,
// and the item and party groups it is limited to.
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { Button, FormControl, Skeleton, toast } from "frappe-ui";
import { call, createDoc, getDoc, updateDoc } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { CHECK_FIELDS } from "@/lib/licenceRules";
import { notLoaded } from "@/offline/reachability";

const DOCTYPE = "Licence Requirement";
const GROUP_TYPES = { Customer: "Customer Group", Supplier: "Supplier Group" };
const props = defineProps({ name: { type: String, default: "" } });

const router = useRouter();
const options = ref(null);
const error = ref("");
const saveError = ref("");
const saving = ref(false);
const form = reactive({
	item_type: "",
	party_type: "Customer",
	action: "Block",
	grace_days: 0,
	is_active: true,
	...Object.fromEntries(CHECK_FIELDS.map((field) => [field, false])),
	item_groups: {},
	party_groups: {},
});

const choices = (values) => values.map((value) => ({ label: value, value }));
const ticked = (map) => Object.keys(map).filter((key) => map[key]);
const summary = (map, none) => {
	const chosen = ticked(map);
	if (!chosen.length) return none;
	return chosen.length === 1 ? chosen[0] : `${chosen.length} chosen`;
};
const partyDocuments = computed(() =>
	options.value.documents.filter((document) => document.party_type === form.party_type)
);
const partyGroups = computed(() =>
	form.party_type === "Supplier" ? options.value.supplier_groups : options.value.customer_groups
);

// A rule is for customers or suppliers, not both: switching drops the other side's choices.
watch(
	() => form.party_type,
	(now, before) => {
		if (!options.value || !before) return;
		form.party_groups = {};
		for (const document of options.value.documents) {
			if (document.party_type !== now) form[document.field] = false;
		}
	}
);

async function save() {
	saveError.value = "";
	if (!form.item_type) {
		saveError.value = "Choose the licence.";
		return;
	}
	saving.value = true;
	const values = {
		item_type: form.item_type,
		party_type: form.party_type,
		action: form.action,
		grace_days: Number(form.grace_days) || 0,
		is_active: form.is_active ? 1 : 0,
		...Object.fromEntries(CHECK_FIELDS.map((field) => [field, form[field] ? 1 : 0])),
		item_groups: ticked(form.item_groups).map((item_group) => ({ item_group })),
		party_groups: ticked(form.party_groups).map((party_group) => ({
			group_type: GROUP_TYPES[form.party_type],
			party_group,
		})),
	};
	try {
		const saved = props.name
			? await updateDoc(DOCTYPE, props.name, values)
			: await createDoc(DOCTYPE, values);
		toast.success(props.name ? "Rule saved" : "Rule added");
		router.replace({ name: "LicenceRules" });
		return saved;
	} catch (err) {
		saveError.value = err.isNetwork
			? "The rule did not reach the server. Try again when you are back online."
			: err.message;
	} finally {
		saving.value = false;
	}
}

const flags = (values) => Object.fromEntries(values.map((value) => [value, true]));

onMounted(async () => {
	try {
		const [loaded, rule] = await Promise.all([
			call("kxcompliance.api.licence_rule_options"),
			props.name ? getDoc(DOCTYPE, props.name) : null,
		]);
		if (rule) {
			Object.assign(form, {
				item_type: rule.item_type,
				party_type: rule.party_type,
				action: rule.action,
				grace_days: rule.grace_days || 0,
				is_active: Boolean(rule.is_active),
				...Object.fromEntries(CHECK_FIELDS.map((field) => [field, Boolean(rule[field])])),
				item_groups: flags((rule.item_groups || []).map((row) => row.item_group)),
				party_groups: flags((rule.party_groups || []).map((row) => row.party_group)),
			});
		}
		options.value = loaded;
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this rule", "opened") : err.message;
	}
});
</script>
