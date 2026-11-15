<template>
	<AppPageHeader
		:title="request ? request.request_type : 'Privacy request'"
		:parent="{ label: 'Privacy requests', route: { name: 'PrivacyRequests' } }"
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
			<Skeleton v-else-if="!request" class="h-48 w-full rounded-lg" />

			<template v-else>
				<section class="flex flex-col gap-2" aria-labelledby="asked-heading">
					<div class="flex items-center gap-2">
						<h2
							id="asked-heading"
							class="flex-1 text-base font-semibold text-ink-gray-8"
						>
							{{ request.requester_name || request.requested_by }} asked
						</h2>
						<Badge
							:label="request.status"
							:theme="REQUEST_STATUS_THEMES[request.status]"
						/>
					</div>
					<p class="whitespace-pre-line text-base text-ink-gray-8">
						{{ request.details }}
					</p>
					<p class="text-sm text-ink-gray-5">
						{{ request.requested_by }} · asked
						{{ formatDateTime(request.received_on) }} · answer due by
						{{ formatDate(request.due_by) }}
					</p>
				</section>

				<p class="rounded-lg bg-surface-gray-1 px-3 py-2 text-sm text-ink-gray-7">
					{{ GUIDANCE[request.request_type] }}
				</p>

				<section
					class="flex flex-col gap-4"
					aria-labelledby="answer-heading"
					data-tour="privacy-answer"
				>
					<h2 id="answer-heading" class="text-base font-semibold text-ink-gray-8">
						Answer
					</h2>
					<FormControl
						v-model="form.status"
						type="select"
						label="Status"
						:options="STATUSES"
						:disabled="!editable"
					/>
					<FormControl
						v-model="form.response"
						type="textarea"
						label="Response"
						description="Sent to them in the app, and by email when the app sends email, once the request is done or declined."
						:disabled="!editable"
					/>
					<p v-if="request.closed_on" class="text-sm text-ink-gray-5">
						Closed {{ formatDateTime(request.closed_on) }} by
						{{ nameOf(request.closed_by) }}.
					</p>
				</section>
			</template>
		</div>
	</RecordFrame>

	<div
		v-if="request && editable"
		class="sticky bottom-0 z-10 mt-auto border-t border-outline-gray-1 bg-surface-base"
	>
		<div
			class="mx-auto flex w-full flex-col-reverse gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-end sm:px-6"
			:class="recordWidth(name)"
		>
			<p v-if="saveError" role="alert" class="text-sm text-ink-red-4 sm:mr-auto">
				{{ saveError }}
			</p>
			<Button variant="solid" label="Save" :loading="saving" @click="save" />
		</div>
	</div>
</template>

<script setup>
// One privacy request: what the person asked, and the manager's answer.
import { onMounted, reactive, ref } from "vue";
import { Badge, Button, FormControl, Skeleton, toast } from "frappe-ui";
import { getDoc, updateDoc } from "@/api";
import { isManager } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import RecordFrame from "@/components/RecordFrame.vue";
import { learnNames, nameOf } from "@/composables/usePeople";
import { formatDate, formatDateTime } from "@/lib/format";
import { REQUEST_STATUS_THEMES } from "@/lib/privacy";
import { recordWidth } from "@/lib/records";
import { notLoaded } from "@/offline/reachability";

const DOCTYPE = "Privacy Request";
const STATUSES = ["Open", "In Progress", "Done", "Declined"].map((value) => ({
	label: value,
	value,
}));
// What answering each kind of request involves.
const GUIDANCE = {
	"See my data":
		"Tell them what the app holds about them: their name, email and role, the records they added or changed, and, as a signatory, their designation, DIN, PAN, email and mobile. A System Manager can email them a full copy from the Desk (Personal Data Download Request).",
	"Correct my data":
		"Correct the record (their name in People, or a signatory's details), then say here what changed.",
	"Erase my data":
		"Remove them from People. Filings, registers and other records the law requires are kept until that period ends: say which. A System Manager can erase the rest from the Desk (Personal Data Deletion Request).",
	Grievance: "Look into it, then say what you found and what was done.",
};

const props = defineProps({ name: { type: String, required: true } });
const request = ref(null);
const form = reactive({ status: "Open", response: "" });
const editable = isManager();
const error = ref("");
const saveError = ref("");
const saving = ref(false);

function show(doc) {
	request.value = doc;
	form.status = doc.status;
	form.response = doc.response || "";
	learnNames([doc.closed_by].filter(Boolean));
}

async function save() {
	saveError.value = "";
	saving.value = true;
	try {
		show(
			await updateDoc(DOCTYPE, props.name, {
				status: form.status,
				response: form.response.trim(),
			})
		);
		toast.success("Saved");
	} catch (err) {
		saveError.value = err.isNetwork
			? "The answer did not reach the server. Try again when you are back online."
			: err.message;
	} finally {
		saving.value = false;
	}
}

onMounted(async () => {
	try {
		show(await getDoc(DOCTYPE, props.name));
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this request", "opened") : err.message;
	}
});
</script>
