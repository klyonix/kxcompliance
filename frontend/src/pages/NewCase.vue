<template>
	<AppPageHeader title="Start a case" :parent="{ label: 'Legal', route: { name: 'Legal' } }" />

	<form
		class="mx-auto flex w-full max-w-xl flex-col gap-5 px-4 py-6 sm:px-6"
		novalidate
		@submit.prevent="save"
	>
		<p class="text-base text-ink-gray-6">
			For a suit, appeal or petition already under way. A notice that has just arrived is
			quicker with Log notice. You hold the case until someone reassigns it.
		</p>

		<p
			v-if="!isConnected()"
			class="flex items-center gap-2 rounded-lg bg-surface-amber-1 px-3 py-2 text-base text-ink-amber-4"
		>
			<span class="lucide-cloud-off size-4 shrink-0" aria-hidden="true" />
			Starting a case needs a connection to the server.
		</p>

		<FormControl
			v-model="form.title"
			label="Title"
			placeholder="Recovery suit against Acme Traders"
			required
			:error="errorFor('title')"
		/>
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<FormControl
				v-model="form.case_type"
				type="select"
				label="Type"
				:options="CASE_TYPES"
				required
			/>
			<FormControl
				v-model="form.our_role"
				type="select"
				label="We are the"
				:options="OUR_ROLES"
				required
			/>
		</div>
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<FormControl
				v-model="form.forum"
				type="select"
				label="Forum"
				:options="FORUMS"
				required
			/>
			<FormControl
				v-model="form.forum_name"
				label="Court or office"
				placeholder="City Civil Court, Bengaluru"
			/>
		</div>
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<FormControl v-model="form.case_number" label="Case number" placeholder="OS 41/2026" />
			<FormControl
				v-model="form.opposing_party"
				label="Opposing party"
				placeholder="Who it is against"
			/>
		</div>
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<FormControl
				v-model="form.filing_date"
				type="date"
				:format="pickerFormat()"
				label="Filed or received on"
				required
				:error="errorFor('filing_date')"
			/>
			<FormControl
				v-model="nextHearing"
				type="date"
				:format="pickerFormat()"
				label="Next hearing"
				description="Optional; it goes on the calendar."
			/>
		</div>
		<FormControl
			v-if="boot.companies.length > 1"
			v-model="form.company"
			type="select"
			label="Company"
			:options="boot.companies"
			required
			:error="errorFor('company')"
		/>

		<p v-if="formError" role="alert" class="text-base text-ink-red-4">{{ formError }}</p>

		<div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
			<Button
				label="Cancel"
				:size="buttonSize"
				:route="{ name: 'Legal', query: { view: 'cases' } }"
				:disabled="saving"
			/>
			<Button
				type="submit"
				variant="solid"
				label="Start case"
				:size="buttonSize"
				:loading="saving"
				:disabled="!isConnected()"
			/>
		</div>
	</form>
</template>

<script setup>
// A case already under way is started from the app: its forum, number and next hearing.
import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { Button, FormControl, toast } from "frappe-ui";
import { call } from "@/api";
import { boot } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { CASE_TYPES, FORUMS, OUR_ROLES } from "@/lib/legal";
import { pickerFormat } from "@/lib/format";
import { isoDate } from "@/lib/obligations";
import { isConnected } from "@/offline/outbox";

const router = useRouter();
const isMobile = useIsMobile();
const buttonSize = computed(() => (isMobile.value ? "md" : "sm"));

const form = reactive({
	title: "",
	case_type: "Litigation",
	our_role: "Petitioner",
	forum: "District Court",
	forum_name: "",
	case_number: "",
	opposing_party: "",
	filing_date: isoDate(new Date()),
	company: boot.defaultCompany || boot.companies[0] || "",
});
const nextHearing = ref("");
const saving = ref(false);
const checking = ref(false);
const formError = ref("");

const REQUIRED = {
	title: "Say what the case is.",
	filing_date: "Pick the date it was filed or received.",
	company: "Pick the company.",
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
			"kxcompliance.api.open_case",
			{
				case: { ...form, title: form.title.trim() },
				next_hearing: nextHearing.value || null,
			},
			{ httpMethod: "POST" }
		);
		toast.success("Case started");
		router.replace({ name: "LegalCase", params: { name } });
	} catch (err) {
		formError.value = err.message;
	} finally {
		saving.value = false;
	}
}
</script>
