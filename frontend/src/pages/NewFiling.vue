<template>
	<AppPageHeader
		title="Add a one-off filing"
		:parent="{ label: 'Filings', route: { name: 'Filings' } }"
	/>

	<form
		class="mx-auto flex w-full max-w-xl flex-col gap-5 px-4 py-6 sm:px-6"
		novalidate
		@submit.prevent="save"
	>
		<p class="text-base text-ink-gray-6">
			For a return outside the company's usual schedule: a revised return, a period it was
			not set up for, a filing asked for once. It follows that return's rules for proof,
			review and payment. A return not in the library is added there first.
		</p>

		<p
			v-if="!isConnected()"
			class="flex items-center gap-2 rounded-lg bg-surface-amber-1 px-3 py-2 text-base text-ink-amber-4"
		>
			<span class="lucide-cloud-off size-4 shrink-0" aria-hidden="true" />
			Adding a filing needs a connection to the server.
		</p>
		<p v-if="loadError" role="alert" class="text-base text-ink-red-4">{{ loadError }}</p>

		<div class="flex flex-col gap-1.5">
			<Combobox
				v-model="form.obligation_template"
				label="Return"
				placeholder="Search the obligation library"
				:options="returnOptions"
				required
			/>
			<p v-if="errorFor('obligation_template')" class="text-sm text-ink-red-4">
				{{ errorFor("obligation_template") }}
			</p>
		</div>
		<div v-if="boot.companies.length > 1" class="flex flex-col gap-1.5">
			<Combobox
				v-model="form.company"
				label="Company"
				placeholder="Search companies"
				:options="boot.companies.map((name) => ({ label: name, value: name }))"
				required
			/>
			<p v-if="errorFor('company')" class="text-sm text-ink-red-4">
				{{ errorFor("company") }}
			</p>
		</div>
		<FormControl
			v-model="form.period_label"
			label="What it is for"
			placeholder="Revised return, Sep 2026"
			required
			:error="errorFor('period_label')"
		/>
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<FormControl
				v-model="form.due_date"
				type="date"
				:format="pickerFormat()"
				label="Due on"
				required
				:error="errorFor('due_date')"
			/>
			<FormControl
				v-model="form.period_end"
				type="date"
				:format="pickerFormat()"
				label="Period ended"
				description="Optional; it groups the filing with others of that period."
			/>
		</div>
		<div v-if="people.length" class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<FormControl
				v-model="form.responsible"
				type="select"
				label="Responsible"
				:options="people"
			/>
			<FormControl
				v-model="form.reviewer"
				type="select"
				label="Reviewer"
				:options="[{ label: 'Company default', value: '' }, ...people]"
			/>
		</div>
		<FormControl
			v-model="form.remarks"
			type="textarea"
			label="Remarks"
			placeholder="Why it is needed, the notice or letter that asked for it"
			:rows="3"
		/>

		<p v-if="formError" role="alert" class="text-base text-ink-red-4">{{ formError }}</p>

		<div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
			<Button
				label="Cancel"
				:size="buttonSize"
				:route="{ name: 'Filings' }"
				:disabled="saving"
			/>
			<Button
				type="submit"
				variant="solid"
				label="Add filing"
				:size="buttonSize"
				:loading="saving"
				:disabled="!isConnected()"
			/>
		</div>
	</form>
</template>

<script setup>
// A filing outside a company's schedule, from a return in the obligation library. Whoever adds
// it holds it; a manager may choose who prepares and who reviews it.
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { Button, Combobox, FormControl, toast } from "frappe-ui";
import { call, getList } from "@/api";
import { boot, isManager } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { pickerFormat } from "@/lib/format";
import { personOptions } from "@/lib/people";
import { returnGroups } from "@/lib/filings";
import { isConnected } from "@/offline/outbox";
import { notLoaded } from "@/offline/reachability";

const router = useRouter();
const isMobile = useIsMobile();
const buttonSize = computed(() => (isMobile.value ? "md" : "sm"));

const form = reactive({
	obligation_template: "",
	company: boot.defaultCompany || boot.companies[0] || "",
	period_label: "",
	due_date: "",
	period_end: "",
	responsible: boot.user,
	reviewer: "",
	remarks: "",
});
const templates = ref([]);
const people = ref([]);
const saving = ref(false);
const checking = ref(false);
const formError = ref("");
const loadError = ref("");

const returnOptions = computed(() => returnGroups(templates.value));

const REQUIRED = {
	obligation_template: "Choose the return.",
	company: "Choose the company.",
	period_label: "Say what it is for.",
	due_date: "Pick the due date.",
};
const errorFor = (field) =>
	checking.value && !String(form[field] || "").trim() ? REQUIRED[field] : "";

async function save() {
	checking.value = true;
	formError.value = "";
	if (Object.keys(REQUIRED).some((field) => errorFor(field))) return;
	saving.value = true;
	try {
		const { name } = await call(
			"kxcompliance.api.add_one_off_filing",
			{
				filing: {
					...form,
					period_label: form.period_label.trim(),
					remarks: form.remarks.trim(),
					// Only a manager names who handles it; anyone else holds it themselves.
					responsible: people.value.length ? form.responsible : "",
					reviewer: people.value.length ? form.reviewer : "",
				},
			},
			{ httpMethod: "POST" }
		);
		toast.success("Filing added");
		router.replace({ name: "ComplianceTask", params: { name } });
	} catch (err) {
		formError.value = err.message;
	} finally {
		saving.value = false;
	}
}

onMounted(async () => {
	try {
		const [library, editable] = await Promise.all([
			getList("Compliance Obligation Template", {
				fields: ["name", "law", "form"],
				filters: [["is_active", "=", 1]],
				orderBy: "name asc",
				limit: 1000,
			}),
			isManager()
				? call("kxcompliance.api.editable_fields", { doctype: "Compliance Task" })
				: { people: [] },
		]);
		templates.value = library.rows;
		people.value = personOptions(editable.people || []);
	} catch (err) {
		loadError.value = err.isNetwork ? notLoaded("the obligation library") : err.message;
	}
});
</script>
