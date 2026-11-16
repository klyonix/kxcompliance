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
				<p v-if="shared" class="text-base text-ink-gray-5">
					{{
						settings.set_by_firm
							? "Shared with other firms. These are your own settings for it; the type itself stays as it is."
							: "Shared with other firms. Saving keeps your own settings for it; the type itself stays as it is."
					}}
				</p>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<FormControl
						v-model="form.category"
						type="select"
						label="Category"
						:disabled="shared"
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
				<FormControl
					v-model="form.description"
					type="textarea"
					label="Notes"
					:rows="3"
					:disabled="shared"
				/>
				<div v-if="shared && settings.set_by_firm">
					<Button
						label="Use the shared settings"
						:loading="restoring"
						@click="useShared"
					/>
				</div>
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
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { Button, FormControl, Skeleton, toast } from "frappe-ui";
import { call, createDoc, getDoc, updateDoc } from "@/api";
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
const restoring = ref(false);
// The type's settings as the firm uses them (kxcompliance.api.item_type_settings_of).
const settings = ref({ values: {}, reminders: [], set_by_firm: false, may_edit_type: true });
// A type shared with other firms: the firm keeps its own settings for it.
const shared = computed(() => Boolean(props.name) && !settings.value.may_edit_type);
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
		if (shared.value) {
			const { category: _category, description: _description, reminders, ...own } = values;
			settings.value = await call(
				"kxcompliance.api.save_item_type_settings",
				{
					item_type: props.name,
					values: own,
					reminders: reminders.map((row) => row.days_before),
				},
				{ httpMethod: "POST" }
			);
			toast.success("Your settings for this type are saved");
			return;
		}
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

// The settings the form shows, from the type or the firm's own.
function fillSettings() {
	const values = settings.value.values;
	Object.assign(form, {
		renewal_cycle_months: values.renewal_cycle_months || 0,
		grace_days: values.grace_days || 0,
		requires_document: Boolean(values.requires_document),
		is_active: Boolean(values.is_active),
		reminder_days: daysText(settings.value.reminders.map((days) => ({ days_before: days }))),
	});
}

async function useShared() {
	restoring.value = true;
	saveError.value = "";
	try {
		settings.value = await call(
			"kxcompliance.api.use_shared_item_type_settings",
			{ item_type: props.name },
			{ httpMethod: "POST" }
		);
		fillSettings();
		toast.success("Back to the shared settings");
	} catch (err) {
		saveError.value = err.message;
	} finally {
		restoring.value = false;
	}
}

onMounted(async () => {
	try {
		if (props.name) {
			const [type, inUse] = await Promise.all([
				getDoc("Compliance Item Type", props.name),
				call("kxcompliance.api.item_type_settings_of", { item_type: props.name }),
			]);
			settings.value = inUse;
			Object.assign(form, {
				category: type.category,
				description: type.description || "",
			});
			fillSettings();
		}
		ready.value = true;
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this item type", "opened") : err.message;
	}
});
</script>
