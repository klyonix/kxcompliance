<template>
	<AppPageHeader
		:title="name || 'Extend a due date'"
		:parent="{ label: 'Extensions', route: { name: 'Extensions' } }"
	/>

	<RecordFrame :doctype="DOCTYPE" :name="name">
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
				<p class="text-base text-ink-gray-6">
					When the government extends a due date, record it here. Open filings for the
					periods it covers move to the new date; filed ones keep the date they were
					filed against.
				</p>
				<FormControl
					v-model="form.obligation_template"
					type="select"
					label="Obligation"
					:options="[{ label: 'Choose an obligation', value: '' }, ...templateOptions]"
				/>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
					<FormControl
						v-model="form.periods_ending_from"
						type="date"
						:format="pickerFormat()"
						label="Periods ending from"
					/>
					<FormControl
						v-model="form.periods_ending_to"
						type="date"
						:format="pickerFormat()"
						label="Periods ending to"
					/>
					<FormControl
						v-model="form.new_due_date"
						type="date"
						:format="pickerFormat()"
						label="New due date"
					/>
				</div>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<FormControl
						v-model="form.notification_reference"
						label="Notification or circular"
						placeholder="Notification 12/2026-Central Tax"
					/>
					<FormControl
						v-model="form.issued_on"
						type="date"
						:format="pickerFormat()"
						label="Issued on"
					/>
				</div>
				<p
					v-if="preview"
					class="rounded-lg bg-surface-gray-2 px-3 py-2 text-base text-ink-gray-7"
					aria-live="polite"
				>
					{{ previewText(preview) }}
				</p>
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
				:label="name ? 'Save' : 'Extend'"
				:loading="saving"
				@click="save"
			/>
		</div>
	</div>
</template>

<script setup>
// Record a government extension of a due date, or change one; shows what it would move first.
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button, FormControl, Skeleton, toast } from "frappe-ui";
import { call, createDoc, getDoc, getList, updateDoc } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import RecordFrame from "@/components/RecordFrame.vue";
import { pickerFormat } from "@/lib/format";
import { previewText } from "@/lib/obligations";
import { recordWidth } from "@/lib/records";
import { notLoaded } from "@/offline/reachability";

const DOCTYPE = "Compliance Due Date Extension";
const FIELDS = [
	"obligation_template",
	"periods_ending_from",
	"periods_ending_to",
	"new_due_date",
	"notification_reference",
	"issued_on",
];

const props = defineProps({ name: { type: String, default: "" } });

const route = useRoute();
const router = useRouter();
const ready = ref(false);
const error = ref("");
const saveError = ref("");
const saving = ref(false);
const templates = ref([]);
const preview = ref(null);
const form = reactive({
	...Object.fromEntries(FIELDS.map((field) => [field, ""])),
	obligation_template: typeof route.query.template === "string" ? route.query.template : "",
});

const templateOptions = computed(() =>
	templates.value.map((name) => ({ label: name, value: name }))
);

// Only the latest preview is shown, so a slow answer cannot replace a newer one.
let latest = 0;
async function loadPreview() {
	const ticket = ++latest;
	const { obligation_template, periods_ending_from, periods_ending_to } = form;
	if (!obligation_template || !periods_ending_from || !periods_ending_to) {
		preview.value = null;
		return;
	}
	try {
		const result = await call("kxcompliance.api.extension_preview", {
			obligation_template,
			periods_ending_from,
			periods_ending_to,
		});
		if (ticket === latest) preview.value = result;
	} catch {
		// The preview only helps; saving still works without it.
		if (ticket === latest) preview.value = null;
	}
}

async function save() {
	saveError.value = "";
	const missing = [
		!form.obligation_template && "the obligation",
		!(form.periods_ending_from && form.periods_ending_to) && "the periods",
		!form.new_due_date && "the new due date",
		!form.notification_reference.trim() && "the notification",
	].filter(Boolean);
	if (missing.length) {
		saveError.value = `Fill in ${missing.join(", ")}.`;
		return;
	}
	saving.value = true;
	const values = Object.fromEntries(FIELDS.map((field) => [field, form[field] || null]));
	try {
		const saved = props.name
			? await updateDoc(DOCTYPE, props.name, values)
			: await createDoc(DOCTYPE, values);
		toast.success("Extension saved; its filings move to the new date in a moment");
		router.replace({ name: "Extension", params: { name: saved.name } });
	} catch (err) {
		saveError.value = err.isNetwork
			? "The extension did not reach the server. Try again when you are back online."
			: err.message;
	} finally {
		saving.value = false;
	}
}

watch(
	() => [form.obligation_template, form.periods_ending_from, form.periods_ending_to],
	loadPreview
);

onMounted(async () => {
	try {
		const [list, extension] = await Promise.all([
			getList("Compliance Obligation Template", {
				fields: ["name"],
				filters: [["is_active", "=", 1]],
				orderBy: "name asc",
				limit: 1000,
			}),
			props.name ? getDoc(DOCTYPE, props.name) : null,
		]);
		templates.value = list.rows.map((row) => row.name);
		if (extension) {
			for (const field of FIELDS) form[field] = extension[field] || "";
			// An extension may be for an obligation since switched off; keep it choosable.
			if (!templates.value.includes(extension.obligation_template))
				templates.value.unshift(extension.obligation_template);
		}
		ready.value = true;
		loadPreview();
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this extension", "opened") : err.message;
	}
});
</script>
