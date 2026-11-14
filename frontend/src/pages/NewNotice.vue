<template>
	<AppPageHeader title="Log a notice" />

	<form
		class="mx-auto flex w-full max-w-xl flex-col gap-5 px-4 py-6 sm:px-6"
		novalidate
		@submit.prevent="save"
	>
		<p class="text-base text-ink-gray-6">
			Record a notice as soon as it arrives, with the date the reply is due. You hold it
			until someone reassigns it; the rest can be filled in later in the Desk.
		</p>

		<p
			v-if="!isConnected()"
			class="flex items-center gap-2 rounded-lg bg-surface-amber-1 px-3 py-2 text-base text-ink-amber-4"
		>
			<span class="lucide-cloud-off size-4 shrink-0" aria-hidden="true" />
			Logging a notice needs a connection to the server.
		</p>

		<FormControl
			v-model="form.title"
			label="What it is"
			placeholder="Show cause notice, GST FY 2024-25"
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
				v-model="form.forum"
				type="select"
				label="From"
				:options="FORUMS"
				required
			/>
		</div>
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<FormControl
				v-model="form.reply_by"
				type="date"
				label="Reply by"
				placeholder="Pick a date"
				required
				:error="errorFor('reply_by')"
			/>
			<FormControl
				v-model="form.notice_reference"
				label="Notice reference"
				placeholder="DIN or reference number"
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

		<div class="flex flex-col gap-1.5">
			<span class="text-xs text-ink-gray-5">Copy of the notice</span>
			<div class="flex items-center gap-3 rounded-lg bg-surface-gray-1 px-3 py-3">
				<span
					class="flex size-9 shrink-0 items-center justify-center rounded-lg bg-surface-base text-ink-gray-6"
				>
					<span
						:class="copy ? 'lucide-file-check' : 'lucide-camera'"
						class="size-5"
						aria-hidden="true"
					/>
				</span>
				<span class="min-w-0 flex-1 truncate text-base text-ink-gray-8">{{
					copy ? copy.name : "A photo or a PDF"
				}}</span>
				<Button :label="copy ? 'Replace' : 'Add'" @click="fileInput?.click()" />
				<input
					ref="fileInput"
					type="file"
					accept="image/*,application/pdf"
					capture="environment"
					class="hidden"
					@change="pickCopy"
				/>
			</div>
		</div>

		<p v-if="formError" role="alert" class="text-base text-ink-red-4">{{ formError }}</p>

		<div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
			<Button
				label="Cancel"
				:size="buttonSize"
				:route="{ name: 'Legal' }"
				:disabled="saving"
			/>
			<Button
				type="submit"
				variant="solid"
				label="Log notice"
				:size="buttonSize"
				:loading="saving"
				:disabled="!isConnected()"
			/>
		</div>
	</form>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { Button, FormControl, toast } from "frappe-ui";
import { call, upload } from "@/api";
import { boot } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { CASE_TYPES, FORUMS } from "@/lib/legal";
import { isConnected } from "@/offline/outbox";

const router = useRouter();
const isMobile = useIsMobile();
const buttonSize = computed(() => (isMobile.value ? "md" : "sm"));

const form = reactive({
	title: "",
	case_type: "Tax Notice or Assessment",
	forum: "Tax Officer",
	reply_by: "",
	notice_reference: "",
	company: boot.defaultCompany || boot.companies[0] || "",
});
const copy = ref(null);
const fileInput = ref(null);
const saving = ref(false);
const checking = ref(false);
const formError = ref("");

const REQUIRED = {
	title: "Say what the notice is.",
	reply_by: "Pick the reply date.",
	company: "Pick the company.",
};
const errorFor = (field) =>
	checking.value && !String(form[field] || "").trim() ? REQUIRED[field] : "";

function pickCopy(event) {
	const file = event.target.files?.[0];
	event.target.value = "";
	if (file) copy.value = file;
}

async function save() {
	checking.value = true;
	formError.value = "";
	if (Object.keys(REQUIRED).some((field) => errorFor(field))) return;
	saving.value = true;
	let name;
	try {
		name = (
			await call(
				"compliance_plus.api.log_notice",
				{ ...form, title: form.title.trim() },
				{ httpMethod: "POST" }
			)
		).name;
	} catch (err) {
		formError.value = err.message;
		saving.value = false;
		return;
	}
	try {
		if (copy.value) {
			await upload(copy.value, {
				doctype: "Legal Case",
				docname: name,
				fileName: copy.value.name,
			});
		}
		toast.success("Notice logged");
	} catch (err) {
		// The notice is saved; only its copy did not go through, and can be added in the Desk.
		toast.error(`Notice logged, but the copy was not attached: ${err.message}`);
	} finally {
		saving.value = false;
	}
	router.replace({ name: "LegalCase", params: { name } });
}
</script>
