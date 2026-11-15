<template>
	<AppPageHeader
		title="Add a trademark"
		:parent="{ label: 'Legal', route: { name: 'Legal', query: { view: 'marks' } } }"
	/>

	<form
		class="mx-auto flex w-full max-w-xl flex-col gap-5 px-4 py-6 sm:px-6"
		novalidate
		@submit.prevent="save"
	>
		<p class="text-base text-ink-gray-6">
			A mark applied for, or one already held. Its validity runs ten years from filing, and
			its stages are recorded on its page as the registry writes. You hold it until someone
			reassigns it.
		</p>

		<p
			v-if="!isConnected()"
			class="flex items-center gap-2 rounded-lg bg-surface-amber-1 px-3 py-2 text-base text-ink-amber-4"
		>
			<span class="lucide-cloud-off size-4 shrink-0" aria-hidden="true" />
			Adding a trademark needs a connection to the server.
		</p>

		<div class="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_12rem]">
			<FormControl
				v-model="form.mark"
				label="Mark"
				placeholder="The word or name of the mark"
				required
				:error="errorFor('mark')"
			/>
			<FormControl
				v-model="form.mark_type"
				type="select"
				label="Kind"
				:options="MARK_TYPES"
				required
			/>
		</div>
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<FormControl
				v-model="form.application_number"
				label="Application number"
				placeholder="From the filing receipt"
			/>
			<FormControl
				v-model="form.filing_date"
				type="date"
				:format="pickerFormat()"
				label="Filed on"
				required
				:error="errorFor('filing_date')"
			/>
		</div>
		<FormControl
			v-if="boot.companies.length > 1"
			v-model="form.applicant"
			type="select"
			label="Applicant"
			:options="boot.companies"
			required
			:error="errorFor('applicant')"
		/>

		<fieldset class="flex flex-col gap-2">
			<legend class="mb-1 text-xs text-ink-gray-5">Classes</legend>
			<div
				v-for="(row, index) in classes"
				:key="index"
				class="grid grid-cols-[5rem_1fr_auto] items-start gap-2"
			>
				<FormControl
					v-model="row.class_number"
					type="number"
					:aria-label="`Class ${index + 1}`"
					placeholder="Class"
				/>
				<FormControl
					v-model="row.goods_or_services"
					:aria-label="`What class ${index + 1} covers`"
					placeholder="Goods or services it covers"
				/>
				<Button
					variant="ghost"
					icon="lucide-x"
					:aria-label="`Remove class ${index + 1}`"
					:disabled="classes.length === 1"
					@click="classes.splice(index, 1)"
				/>
			</div>
			<p v-if="checking && classesProblem" role="alert" class="text-sm text-ink-red-4">
				{{ classesProblem }}
			</p>
			<div>
				<Button
					icon-left="lucide-plus"
					label="Add a class"
					@click="classes.push({ class_number: '', goods_or_services: '' })"
				/>
			</div>
		</fieldset>

		<p v-if="formError" role="alert" class="text-base text-ink-red-4">{{ formError }}</p>

		<div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
			<Button
				label="Cancel"
				:size="buttonSize"
				:route="{ name: 'Legal', query: { view: 'marks' } }"
				:disabled="saving"
			/>
			<Button
				type="submit"
				variant="solid"
				label="Add trademark"
				:size="buttonSize"
				:loading="saving"
				:disabled="!isConnected()"
			/>
		</div>
	</form>
</template>

<script setup>
// A trademark is added from the app: the mark, its application and its classes.
import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { Button, FormControl, toast } from "frappe-ui";
import { call } from "@/api";
import { boot } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { MARK_TYPES, classesError } from "@/lib/legal";
import { pickerFormat } from "@/lib/format";
import { isConnected } from "@/offline/outbox";

const router = useRouter();
const isMobile = useIsMobile();
const buttonSize = computed(() => (isMobile.value ? "md" : "sm"));

const form = reactive({
	mark: "",
	mark_type: "Word",
	application_number: "",
	filing_date: "",
	applicant: boot.defaultCompany || boot.companies[0] || "",
});
const classes = ref([{ class_number: "", goods_or_services: "" }]);
const saving = ref(false);
const checking = ref(false);
const formError = ref("");

const REQUIRED = {
	mark: "Give the mark.",
	filing_date: "Pick the date it was filed.",
	applicant: "Pick the applicant.",
};
const errorFor = (field) =>
	checking.value && !String(form[field] || "").trim() ? REQUIRED[field] : "";
const classesProblem = computed(() => classesError(classes.value));

async function save() {
	checking.value = true;
	formError.value = "";
	if (Object.keys(REQUIRED).some((field) => errorFor(field)) || classesProblem.value) return;
	saving.value = true;
	try {
		const { name } = await call(
			"kxcompliance.api.add_trademark",
			{
				mark: { ...form, mark: form.mark.trim() },
				classes: classes.value.map((row) => ({
					class_number: Number(row.class_number),
					goods_or_services: String(row.goods_or_services || "").trim() || null,
				})),
			},
			{ httpMethod: "POST" }
		);
		toast.success("Trademark added");
		router.replace({ name: "Trademark", params: { name } });
	} catch (err) {
		formError.value = err.message;
	} finally {
		saving.value = false;
	}
}
</script>
