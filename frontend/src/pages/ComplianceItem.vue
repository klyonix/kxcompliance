<template>
	<AppPageHeader :title="item?.title || 'Item'">
		<template #actions>
			<Button
				v-if="canRenew && !isMobile"
				variant="solid"
				label="Start renewal"
				:disabled="!outbox.online"
				:tooltip="outbox.online ? undefined : 'Starting a renewal needs a connection'"
				@click="startRenewal"
			/>
			<Dropdown v-if="item" :options="menu" align="end">
				<Button variant="ghost" icon="lucide-ellipsis" label="More actions" />
			</Dropdown>
		</template>
	</AppPageHeader>

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-6 sm:px-6">
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>

		<div v-else-if="!item" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton class="h-6 w-1/2 rounded" />
			<Skeleton class="h-4 w-1/3 rounded" />
			<Skeleton class="mt-4 h-32 w-full rounded-lg" />
		</div>

		<template v-else>
			<section class="flex flex-col gap-2">
				<div class="flex flex-wrap items-center gap-2">
					<Badge :label="item.status" :theme="itemTheme(item.status)" size="md" />
					<span
						class="text-base"
						:class="
							row.due.late && !item.is_cancelled
								? 'font-medium text-ink-red-4'
								: 'text-ink-gray-6'
						"
					>
						{{ validity }}
					</span>
				</div>
				<p
					v-if="item.is_cancelled"
					class="rounded-lg bg-surface-gray-2 px-3 py-2 text-base text-ink-gray-7"
				>
					Cancelled: {{ item.cancellation_reason }}
				</p>
				<!-- On a phone the header has room for the title only, so the main action sits here. -->
				<Button
					v-if="canRenew && isMobile"
					class="mt-2 w-full"
					size="md"
					variant="solid"
					label="Start renewal"
					:disabled="!outbox.online"
					@click="startRenewal"
				/>
				<p v-if="canRenew && isMobile && !outbox.online" class="text-sm text-ink-gray-5">
					Starting a renewal needs a connection.
				</p>
			</section>

			<section class="flex flex-col gap-3" aria-labelledby="certificate-heading">
				<h2 id="certificate-heading" class="text-base font-semibold text-ink-gray-8">
					Certificate
				</h2>
				<div class="flex items-center gap-3 rounded-lg bg-surface-gray-1 px-3 py-3">
					<span
						class="flex size-9 shrink-0 items-center justify-center rounded-lg bg-surface-base text-ink-gray-6"
					>
						<span
							:class="item.certificate ? 'lucide-file-check' : 'lucide-file-plus'"
							class="size-5"
							aria-hidden="true"
						/>
					</span>
					<div class="flex min-w-0 flex-1 flex-col">
						<span class="truncate text-base text-ink-gray-8">{{
							certificateLabel
						}}</span>
						<span v-if="pendingCertificate" class="text-sm text-ink-amber-4"
							>Waiting to send</span
						>
						<span v-else-if="!item.certificate" class="text-sm text-ink-gray-5"
							>A photo or a PDF of the current certificate</span
						>
					</div>
					<Button
						v-if="item.certificate"
						label="View"
						:href="item.certificate"
						target="_blank"
					/>
					<Button
						v-if="mayAct"
						:label="item.certificate ? 'Replace' : 'Attach'"
						@click="chooseFile"
					/>
					<input
						ref="fileInput"
						type="file"
						accept="image/*,application/pdf"
						class="hidden"
						@change="attachCertificate"
					/>
				</div>
			</section>

			<section class="flex flex-col gap-3" aria-labelledby="details-heading">
				<h2 id="details-heading" class="text-base font-semibold text-ink-gray-8">
					Details
				</h2>
				<dl class="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
					<div v-for="fact in facts" :key="fact.label" class="flex flex-col gap-0.5">
						<dt class="text-sm text-ink-gray-5">{{ fact.label }}</dt>
						<dd class="text-base text-ink-gray-8">{{ fact.value }}</dd>
					</div>
				</dl>
			</section>

			<section class="flex flex-col gap-3" aria-labelledby="renewals-heading">
				<h2 id="renewals-heading" class="text-base font-semibold text-ink-gray-8">
					Renewals
				</h2>
				<p v-if="!renewals.length" class="text-base text-ink-gray-5">
					No renewals recorded yet.
				</p>
				<div
					v-for="renewal in renewals"
					:key="renewal.name"
					class="flex items-center gap-3 px-1"
				>
					<span class="flex min-w-0 flex-1 flex-col">
						<span class="text-base text-ink-gray-8">{{ renewalTitle(renewal) }}</span>
						<span class="truncate text-sm text-ink-gray-5">{{
							renewalDetail(renewal)
						}}</span>
					</span>
					<Badge :label="renewal.status" :theme="renewalTheme(renewal.status)" />
				</div>
			</section>
		</template>
	</div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { Badge, Button, Dropdown, Skeleton, dialog, toast } from "frappe-ui";
import { createDoc, getDoc, getList, runMethod } from "@/api";
import { boot } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { OPEN_RENEWAL_STATUSES, canAct, itemRow, itemTheme } from "@/lib/items";
import { deskRoute } from "@/navigation";
import { outbox, refresh as refreshOutbox } from "@/offline/outbox";
import { submit } from "@/offline/queue";
import { formatDate } from "@/lib/format";

const props = defineProps({ name: { type: String, required: true } });

const item = ref(null);
const renewals = ref([]);
const error = ref("");
const pendingCertificate = ref("");
const fileInput = ref(null);

const row = computed(() => itemRow(item.value));
const mayAct = computed(() => canAct(item.value, boot));
const openRenewal = computed(() =>
	renewals.value.find((renewal) => OPEN_RENEWAL_STATUSES.includes(renewal.status))
);
const canRenew = computed(() => Boolean(item.value) && mayAct.value && !openRenewal.value);
const isMobile = useIsMobile();

const validity = computed(() => {
	if (!item.value.valid_until) return "Does not expire";
	const until = `Valid until ${formatDate(item.value.valid_until)}`;
	return item.value.is_cancelled ? until : `${until} · ${row.value.due.text.toLowerCase()}`;
});

const certificateLabel = computed(() => {
	if (pendingCertificate.value) return pendingCertificate.value;
	if (!item.value.certificate) return "No certificate attached";
	return decodeURIComponent(item.value.certificate.split("/").pop());
});

const facts = computed(() =>
	[
		["Type", item.value.item_type],
		["Reference number", item.value.reference_number],
		[
			"Held by",
			item.value.holder_type === "Company"
				? item.value.company
				: `${item.value.holder} (${item.value.holder_type})`,
		],
		["Company", item.value.holder_type === "Company" ? "" : item.value.company],
		["Branch", item.value.branch],
		["State", item.value.state],
		["Issuing authority", item.value.issuing_authority],
		["Issued on", formatDate(item.value.issue_date)],
		["Valid from", formatDate(item.value.valid_from)],
		["Responsible", item.value.responsible],
		["Reviewer", item.value.reviewer],
	]
		.filter(([, value]) => value)
		.map(([label, value]) => ({ label, value }))
);

const menu = computed(() => [
	{
		label: "Open in the Desk",
		icon: "lucide-app-window",
		onClick: () => (window.location.href = deskRoute("Compliance Item", props.name)),
	},
	...(mayAct.value
		? [
				{
					label: "Cancel item",
					icon: "lucide-ban",
					theme: "red",
					onClick: cancelItem,
					disabled: !outbox.online,
				},
		  ]
		: []),
]);

const renewalTitle = (renewal) =>
	renewal.new_valid_until
		? `Renewed until ${formatDate(renewal.new_valid_until)}`
		: {
				Applied: "Applied for renewal",
				Planned: "Renewal planned",
				Rejected: "Renewal refused",
				Withdrawn: "Renewal withdrawn",
		  }[renewal.status] || "Renewal";
const renewalDetail = (renewal) =>
	[
		renewal.applied_on && `Applied ${formatDate(renewal.applied_on)}`,
		renewal.application_reference,
	]
		.filter(Boolean)
		.join(" · ");
const renewalTheme = (status) =>
	({ Approved: "green", Applied: "blue", Planned: "gray", Rejected: "red" }[status] || "gray");

async function load() {
	error.value = "";
	try {
		item.value = await getDoc("Compliance Item", props.name);
		renewals.value = (
			await getList("Compliance Renewal", {
				fields: [
					"name",
					"status",
					"applied_on",
					"application_reference",
					"new_valid_until",
				],
				filters: [["compliance_item", "=", props.name]],
				orderBy: "creation desc",
				limit: 50,
			})
		).rows;
	} catch (err) {
		error.value = err.isNetwork
			? "You are offline, and this item has not been opened on this device yet."
			: err.message;
	}
}

const chooseFile = () => fileInput.value?.click();

async function attachCertificate(event) {
	const file = event.target.files?.[0];
	event.target.value = "";
	if (!file) return;
	try {
		const result = await submit({
			doctype: "Compliance Item",
			name: props.name,
			values: {},
			baseModified: item.value.modified,
			files: [{ field: "certificate", blob: file, fileName: file.name }],
		});
		if (result.queued) {
			pendingCertificate.value = file.name;
			toast.info("Saved on this device. It will be sent when you reconnect.");
		} else {
			toast.success("Certificate attached");
			await load();
		}
	} catch (err) {
		toast.error(err.message);
	} finally {
		await refreshOutbox();
	}
}

function startRenewal() {
	dialog.prompt({
		title: "Start renewal",
		message: `For ${item.value.title}. Approving it later moves the item's dates and certificate.`,
		confirmLabel: "Start renewal",
		fields: [
			{
				name: "status",
				label: "Stage",
				type: "select",
				defaultValue: "Applied",
				options: [
					{ label: "Applied for", value: "Applied" },
					{ label: "Planned, not applied yet", value: "Planned" },
				],
			},
			{
				name: "application_reference",
				label: "Application reference",
				placeholder: "Acknowledgement or file number",
			},
		],
		onConfirm: async ({ values }) => {
			await createDoc("Compliance Renewal", { compliance_item: props.name, ...values });
			toast.success("Renewal started");
			await load();
		},
	});
}

function cancelItem() {
	dialog.prompt({
		title: "Cancel item",
		message:
			"It stays in the register as cancelled, with your reason, and gets no more reminders.",
		theme: "red",
		confirmLabel: "Cancel item",
		fields: [{ name: "reason", label: "Reason", type: "textarea", required: true }],
		onConfirm: async ({ values }) => {
			await runMethod("Compliance Item", props.name, "cancel_item", {
				reason: values.reason,
			});
			toast.success("Item cancelled");
			await load();
		},
	});
}

watch(() => props.name, load);
onMounted(load);
</script>
