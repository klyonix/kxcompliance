<template>
	<AppPageHeader :title="request?.title || t('Document request')" :parent="parent">
		<template #actions>
			<Dropdown v-if="request && menu.length" :options="menu" align="end">
				<Button variant="ghost" icon="lucide-ellipsis" label="More actions" />
			</Dropdown>
		</template>
	</AppPageHeader>

	<RecordFrame doctype="Document Request" :name="name" :modified="request?.modified || ''">
		<div class="flex flex-col gap-8">
			<p
				v-if="error"
				role="alert"
				class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
			>
				{{ error }}
			</p>

			<div v-else-if="!request" class="flex flex-col gap-3" aria-busy="true">
				<Skeleton class="h-6 w-1/2 rounded" />
				<Skeleton class="h-4 w-1/3 rounded" />
				<Skeleton class="mt-4 h-32 w-full rounded-lg" />
			</div>

			<template v-else>
				<section class="flex flex-col gap-2">
					<div class="flex flex-wrap items-center gap-2">
						<Badge :label="t(state.label)" :theme="state.theme" size="md" />
						<span
							class="text-base"
							:class="
								row.due.late ? 'font-medium text-ink-red-4' : 'text-ink-gray-6'
							"
							>{{ dueLine }}</span
						>
					</div>
					<p class="text-base text-ink-gray-6">{{ request.company }}</p>
					<p
						v-if="request.status === 'Requested' && request.firm_note"
						class="rounded-lg bg-surface-amber-1 px-3 py-2 text-base text-ink-amber-4"
					>
						{{ t("Sent back: {0}", request.firm_note) }}
					</p>
					<p
						v-else-if="request.status === 'Uploaded'"
						class="rounded-lg bg-surface-gray-2 px-3 py-2 text-base text-ink-gray-7"
					>
						{{
							clientLogin
								? t("Your firm has it and will check it.")
								: t(
										"Check the upload, then accept it or send it back with a note."
								  )
						}}
					</p>
				</section>

				<!-- The firm changes what it asked for, by when, while the request is open. -->
				<EditableDetails
					v-if="!clientLogin"
					doctype="Document Request"
					:name="name"
					:doc="request"
					:details="REQUEST_DETAILS"
					:may-edit="mayChange"
					@saved="load"
				/>
				<section
					v-else-if="request.details"
					class="flex flex-col gap-2"
					aria-labelledby="needed-heading"
				>
					<h2 id="needed-heading" class="text-base font-semibold text-ink-gray-8">
						{{ t("What is needed") }}
					</h2>
					<p class="whitespace-pre-line text-base text-ink-gray-8">
						{{ request.details }}
					</p>
				</section>

				<section class="flex flex-col gap-3" aria-labelledby="documents-heading">
					<div class="flex items-center justify-between gap-3">
						<h2 id="documents-heading" class="text-base font-semibold text-ink-gray-8">
							{{ t("Documents") }}
						</h2>
						<template v-if="mayUpload">
							<Button
								:variant="clientLogin && !documents.length ? 'solid' : 'subtle'"
								icon-left="lucide-upload"
								:label="t('Upload')"
								:loading="uploading"
								@click="input?.click()"
							/>
							<input
								ref="input"
								type="file"
								:accept="DOCUMENT_TYPES"
								class="hidden"
								@change="sendDocument"
							/>
						</template>
					</div>
					<p v-if="uploadError" role="alert" class="text-base text-ink-red-4">
						{{ uploadError }}
					</p>
					<p v-if="documentsError" role="alert" class="text-base text-ink-red-4">
						{{ documentsError }}
					</p>
					<p v-else-if="!documents.length" class="text-base text-ink-gray-5">
						{{
							clientLogin
								? t("Nothing uploaded yet.")
								: t("The client has not uploaded yet.")
						}}
					</p>
					<ul class="flex flex-col">
						<li v-for="document in documents" :key="document.name">
							<a
								:href="document.file_url"
								target="_blank"
								class="flex items-center gap-3 rounded-lg px-1 py-1.5 hover:bg-surface-gray-2"
							>
								<span
									class="lucide-file-text size-4 shrink-0 text-ink-gray-5"
									aria-hidden="true"
								/>
								<span class="min-w-0 flex-1 truncate text-base text-ink-gray-8">{{
									document.file_name
								}}</span>
								<span class="shrink-0 text-sm text-ink-gray-5">{{
									formatDate(document.creation)
								}}</span>
							</a>
						</li>
					</ul>
				</section>

				<section class="flex flex-col gap-3" aria-labelledby="details-heading">
					<h2 id="details-heading" class="text-base font-semibold text-ink-gray-8">
						{{ t("Details") }}
					</h2>
					<dl class="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
						<div v-for="fact in facts" :key="fact.label" class="flex flex-col gap-0.5">
							<dt class="text-sm text-ink-gray-5">{{ t(fact.label) }}</dt>
							<dd class="text-base text-ink-gray-8">
								<RouterLink
									v-if="fact.to"
									:to="fact.to"
									class="underline decoration-outline-gray-3 underline-offset-2"
									>{{ fact.value }}</RouterLink
								>
								<template v-else>{{ fact.value }}</template>
							</dd>
						</div>
					</dl>
				</section>
			</template>
		</div>
	</RecordFrame>

	<div
		v-if="request && mayCheck"
		class="sticky bottom-0 z-10 mt-auto border-t border-outline-gray-1 bg-surface-base"
	>
		<div
			class="mx-auto flex w-full flex-col-reverse gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-end sm:px-6"
			:class="recordWidth(name)"
		>
			<p v-if="actionError" role="alert" class="text-sm text-ink-red-4 sm:mr-auto">
				{{ actionError }}
			</p>
			<Button
				label="Send back"
				:size="buttonSize"
				:disabled="Boolean(busy)"
				@click="sendBack"
			/>
			<Button
				variant="solid"
				label="Accept"
				:size="buttonSize"
				:loading="busy === 'accept'"
				:disabled="Boolean(busy)"
				@click="act('accept')"
			/>
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { Badge, Button, Dropdown, Skeleton, dialog, toast } from "frappe-ui";
import { call, getDoc, runMethod, uploadRequestDocument } from "@/api";
import { isClientLogin, mayRecord } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import EditableDetails from "@/components/EditableDetails.vue";
import RecordFrame from "@/components/RecordFrame.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { learnNames, nameOf } from "@/composables/usePeople";
import { formatDate } from "@/lib/format";
import { useLinkTitle } from "@/lib/linkTitle";
import { t } from "@/lib/i18n";
import { OPEN_REQUEST_STATUSES, requestRow, requestState } from "@/lib/requests";
import { recordWidth } from "@/lib/records";
import { deskActions } from "@/navigation";
import { notLoaded } from "@/offline/reachability";

const props = defineProps({ name: { type: String, required: true } });

const DOCUMENT_TYPES = "image/*,application/pdf,.csv,.txt,.doc,.docx,.xls,.xlsx";
const clientLogin = isClientLogin();

const request = ref(null);
const documents = ref([]);
const error = ref("");
const input = ref(null);
const uploading = ref(false);
const uploadError = ref("");
const busy = ref("");
const actionError = ref("");

const isMobile = useIsMobile();
const buttonSize = computed(() => (isMobile.value ? "md" : "sm"));

const state = computed(() => requestState(request.value, { client: clientLogin }));
const row = computed(() => requestRow(request.value, { client: clientLogin }));
const isOpen = computed(() => OPEN_REQUEST_STATUSES.includes(request.value?.status));
// The firm may also upload a document the client sent another way.
const mayUpload = computed(() => isOpen.value && (clientLogin || mayRecord()));
// Changed only while open; the client is told of a change while it waits on them.
const mayChange = computed(() => !clientLogin && mayRecord() && isOpen.value);
const REQUEST_DETAILS = [
	{ field: "title", label: "Document" },
	{ field: "due_date", label: "Needed by" },
	{ field: "details", label: "Details for the client" },
];
const mayCheck = computed(
	() => !clientLogin && mayRecord() && request.value?.status === "Uploaded"
);

const clientName = useLinkTitle("Compliance Client", () => request.value?.client);
// A request belongs to its client's page; a client's own login goes back to Home.
const parent = computed(() => {
	if (clientLogin) return { label: "Home", route: { name: "ClientHome" } };
	if (!request.value?.client) return { label: "Clients", route: { name: "Clients" } };
	return {
		label: clientName.value,
		route: { name: "Client", params: { name: request.value.client } },
	};
});

const dueLine = computed(() => {
	const due = t("Needed by {0}", formatDate(request.value.due_date));
	return row.value.due.text ? `${due} · ${row.value.due.text.toLowerCase()}` : due;
});

const facts = computed(() =>
	[
		[
			"Filing",
			request.value.filing_label || request.value.compliance_task,
			request.value.compliance_task && {
				name: "ComplianceTask",
				params: { name: request.value.compliance_task },
			},
		],
		["Company", request.value.company],
		["Asked by", nameOf(request.value.requested_by)],
		["Uploaded", formatDate(request.value.uploaded_on)],
		["Accepted by", nameOf(request.value.accepted_by)],
	]
		.filter(([, value]) => value)
		.map(([label, value, to]) => ({ label, value, to }))
);

const menu = computed(() => [
	...deskActions("Document Request", props.name),
	...(!clientLogin && mayRecord() && isOpen.value
		? [
				{
					label: "Withdraw request",
					icon: "lucide-circle-slash",
					onClick: () => act("withdraw", "Request withdrawn"),
				},
		  ]
		: []),
]);

const documentsError = ref("");

async function loadDocuments() {
	try {
		documents.value = await call("kxcompliance.api.documents", {
			doctype: "Document Request",
			name: props.name,
		});
		documentsError.value = "";
	} catch (err) {
		// The request is still useful without them, offline included; say they did not load.
		documents.value = [];
		documentsError.value = err.isNetwork
			? t("The documents could not be loaded. They show again once you are back online.")
			: err.message;
	}
}

async function load() {
	error.value = "";
	try {
		request.value = await getDoc("Document Request", props.name);
		learnNames([request.value.requested_by, request.value.accepted_by]);
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this request", "opened") : err.message;
	}
	await loadDocuments();
}

async function sendDocument(event) {
	const file = event.target.files?.[0];
	event.target.value = "";
	if (!file) return;
	uploading.value = true;
	uploadError.value = "";
	try {
		await uploadRequestDocument(file, props.name);
		toast.success(`${file.name} uploaded`);
		await load();
	} catch (err) {
		uploadError.value = err.isNetwork
			? "The upload did not reach the server. Try again when you are back online."
			: err.message;
	} finally {
		uploading.value = false;
	}
}

async function act(method, done = "Accepted", args = {}) {
	busy.value = method;
	actionError.value = "";
	try {
		await runMethod("Document Request", props.name, method, args);
		toast.success(done);
		await load();
	} catch (err) {
		actionError.value = err.isNetwork
			? "That did not reach the server. Try again when you are back online."
			: err.message;
	} finally {
		busy.value = "";
	}
}

function sendBack() {
	dialog.prompt({
		title: "Send back",
		message: "The client is emailed your note and asked to upload it again.",
		confirmLabel: "Send back",
		fields: [{ name: "note", label: "What is wrong", type: "textarea", required: true }],
		onConfirm: ({ values }) =>
			act("send_back", "Sent back to the client", { note: values.note }),
	});
}

watch(() => props.name, load);
onMounted(load);
</script>
