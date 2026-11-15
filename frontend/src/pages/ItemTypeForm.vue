<template>
	<AppPageHeader
		:title="name || 'New item type'"
		:parent="{ label: 'Item types', route: { name: 'ItemTypes' } }"
	/>

	<RecordFrame doctype="Compliance Item Type" :name="name">
		<div class="flex flex-col gap-6">
			<p
				v-if="error"
				role="alert"
				class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
			>
				{{ error }}
			</p>
			<Skeleton v-else-if="!ready" class="h-48 w-full rounded-lg" />

			<template v-else>
				<FormControl
					v-if="!name"
					v-model="form.type_name"
					label="Name"
					placeholder="Trade Licence"
				/>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<FormControl
						v-model="form.category"
						type="select"
						label="Category"
						:options="CATEGORIES.map((value) => ({ label: value, value }))"
					/>
					<FormControl
						v-model="form.renewal_cycle_months"
						type="number"
						label="Renews every (months; 0 if it does not expire)"
					/>
					<FormControl
						v-model="form.grace_days"
						type="number"
						label="Still valid after expiry for (days)"
					/>
					<FormControl
						v-model="form.reminder_days"
						label="Remind (days before expiry)"
						placeholder="60, 30, 7"
						description="New items of this type take these days; items already recorded keep theirs."
					/>
				</div>
				<FormControl
					v-model="form.requires_document"
					type="checkbox"
					label="A certificate is needed before an item counts as active"
				/>
				<FormControl v-model="form.is_active" type="checkbox" label="In use" />
				<FormControl v-model="form.description" type="textarea" label="Notes" :rows="3" />
			</template>
		</div>
	</RecordFrame>

	<div
		v-if="ready"
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
				:label="name ? 'Save' : 'Add type'"
				:loading="saving"
				@click="save"
			/>
		</div>
	</div>
</template>

<script setup>
// A register item type: how its items renew and when they are reminded.
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { Button, FormControl, Skeleton, toast } from "frappe-ui";
import { createDoc, getDoc, updateDoc } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import RecordFrame from "@/components/RecordFrame.vue";
import { CATEGORIES, daysText, parseDays } from "@/lib/itemTypes";
import { recordWidth } from "@/lib/records";
import { notLoaded } from "@/offline/reachability";

const props = defineProps({ name: { type: String, default: "" } });

const router = useRouter();
const ready = ref(false);
const error = ref("");
const saveError = ref("");
const saving = ref(false);
const form = reactive({
	type_name: "",
	category: "Licence",
	renewal_cycle_months: 12,
	grace_days: 0,
	requires_document: true,
	is_active: true,
	reminder_days: "60, 30, 7",
	description: "",
});

async function save() {
	saveError.value = "";
	if (!props.name && !form.type_name.trim()) {
		saveError.value = "Give the type a name.";
		return;
	}
	saving.value = true;
	const values = {
		category: form.category,
		renewal_cycle_months: Number(form.renewal_cycle_months) || 0,
		grace_days: Number(form.grace_days) || 0,
		requires_document: form.requires_document ? 1 : 0,
		is_active: form.is_active ? 1 : 0,
		reminders: parseDays(form.reminder_days).map((days) => ({ days_before: days })),
		description: form.description,
	};
	try {
		const saved = props.name
			? await updateDoc("Compliance Item Type", props.name, values)
			: await createDoc("Compliance Item Type", {
					type_name: form.type_name.trim(),
					...values,
			  });
		toast.success(props.name ? "Type saved" : "Type added");
		router.replace({ name: "ItemType", params: { name: saved.name } });
	} catch (err) {
		saveError.value = err.isNetwork
			? "The type did not reach the server. Try again when you are back online."
			: err.message;
	} finally {
		saving.value = false;
	}
}

onMounted(async () => {
	try {
		if (props.name) {
			const type = await getDoc("Compliance Item Type", props.name);
			Object.assign(form, {
				category: type.category,
				renewal_cycle_months: type.renewal_cycle_months || 0,
				grace_days: type.grace_days || 0,
				requires_document: Boolean(type.requires_document),
				is_active: Boolean(type.is_active),
				reminder_days: daysText(type.reminders),
				description: type.description || "",
			});
		}
		ready.value = true;
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this item type", "opened") : err.message;
	}
});
</script>
