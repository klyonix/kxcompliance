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
						{{ formatDateTime(request.received_on) }} · answer by
						{{ formatDate(request.due_by) }}
						<template v-if="request.latest_by">
							· latest by law {{ formatDate(request.latest_by) }}</template
						>
					</p>
				</section>

				<p class="rounded-lg bg-surface-gray-1 px-3 py-2 text-sm text-ink-gray-7">
					{{ GUIDANCE[request.request_type] }}
				</p>

				<section
					v-if="editable && request.request_type === 'See my data'"
					class="flex flex-col gap-3"
					aria-labelledby="their-data-heading"
				>
					<h2 id="their-data-heading" class="text-base font-semibold text-ink-gray-8">
						What the app holds about them
					</h2>
					<div v-if="!theirData">
						<Button
							label="Show their data"
							icon-left="lucide-file-user"
							:loading="loadingData"
							@click="showTheirData"
						/>
					</div>
					<PersonalData v-else :data="theirData" />
				</section>

				<section
					v-if="editable && request.request_type === 'Erase my data'"
					class="flex flex-col gap-3"
					aria-labelledby="erase-heading"
				>
					<h2 id="erase-heading" class="text-base font-semibold text-ink-gray-8">
						Erase this person
					</h2>
					<p v-if="request.erased_on" class="text-base text-ink-gray-7">
						Erased {{ formatDateTime(request.erased_on) }}.
					</p>
					<p
						v-else-if="request.status === 'In Progress' && erasing"
						class="text-base text-ink-gray-7"
					>
						Erasing in the background. You are told when it is done.
					</p>
					<template v-else-if="!['Done', 'Declined'].includes(request.status)">
						<p class="text-base text-ink-gray-7">
							Their open work goes to the person you choose. Then their login is
							switched off and renamed, and their name, mobile and photo removed;
							filings keep the work, as done by an erased person. As a signatory they
							keep name, designation and DIN; PAN, email and mobile go. They get your
							answer before their address is removed.
						</p>
						<div>
							<Button
								theme="red"
								label="Erase…"
								icon-left="lucide-user-x"
								@click="openErase"
							/>
						</div>
					</template>
				</section>

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

	<Dialog
		v-model:open="confirming"
		title="Erase this person?"
		:actions="[
			{
				label: 'Erase',
				variant: 'solid',
				theme: 'red',
				onClick: ({ close }) => erase(close),
			},
		]"
	>
		<form class="flex flex-col gap-4" @submit.prevent>
			<FormControl
				v-model="eraseForm.handTo"
				type="select"
				label="Their open work goes to"
				:options="handToOptions"
			/>
			<FormControl
				v-model="eraseForm.confirm"
				:label="`Type ${request?.requested_by} to confirm`"
				autocomplete="off"
			/>
			<p class="text-sm text-ink-gray-5">This cannot be undone.</p>
			<p v-if="eraseError" role="alert" class="text-sm text-ink-red-4">{{ eraseError }}</p>
		</form>
	</Dialog>
</template>

<script setup>
// One privacy request: what the person asked, and the manager's answer.
import { computed, onMounted, reactive, ref } from "vue";
import { Badge, Button, Dialog, FormControl, Skeleton, toast } from "frappe-ui";
import { call, getDoc, updateDoc } from "@/api";
import { isManager } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import PersonalData from "@/components/PersonalData.vue";
import RecordFrame from "@/components/RecordFrame.vue";
import { learnNames, nameOf } from "@/composables/usePeople";
import { formatDate, formatDateTime } from "@/lib/format";
import { personOptions } from "@/lib/people";
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
		'Press "Show their data" for what the app holds about them, and send it to them with your answer. They can also see it themselves, any time, from Account.',
	"Correct my data":
		"Correct the record (their name in People, or a signatory's details), then say here what changed.",
	"Erase my data":
		"Erase them below. Their open work is handed over first, and the records the law requires are kept without their name. Say in the answer what was kept, and why.",
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

const theirData = ref(null);
const loadingData = ref(false);

async function showTheirData() {
	loadingData.value = true;
	try {
		theirData.value = await call("kxcompliance.api.privacy_request_data", {
			request: props.name,
		});
	} catch (err) {
		toast.error(err.message);
	} finally {
		loadingData.value = false;
	}
}

const confirming = ref(false);
const erasing = ref(false);
const eraseError = ref("");
const eraseForm = reactive({ handTo: "", confirm: "" });
const people = ref([]);
const handToOptions = computed(() =>
	personOptions(people.value.filter((person) => person.name !== request.value?.requested_by))
);

async function openErase() {
	eraseError.value = "";
	confirming.value = true;
	if (!people.value.length) {
		people.value = await call("kxcompliance.api.people_options").catch(() => []);
		eraseForm.handTo = handToOptions.value[0]?.value || "";
	}
}

async function erase(close) {
	eraseError.value = "";
	try {
		await call(
			"kxcompliance.api.erase_privacy_requester",
			{ request: props.name, hand_to: eraseForm.handTo, confirm: eraseForm.confirm },
			{ httpMethod: "POST" }
		);
		close();
		erasing.value = true;
		show(await getDoc(DOCTYPE, props.name));
		toast.success("Erasing in the background. You are told when it is done.");
	} catch (err) {
		eraseError.value = err.message;
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
