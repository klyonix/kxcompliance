<template>
	<section class="flex flex-col gap-3" aria-labelledby="privacy-heading">
		<div class="flex flex-col gap-0.5">
			<h2 id="privacy-heading" class="text-base font-semibold text-ink-gray-8">
				{{ t("Your privacy") }}
			</h2>
			<p class="text-sm text-ink-gray-5">
				{{
					t(
						"See what the app holds about you, ask to have it corrected or erased, or raise a grievance. A manager answers within 30 days, and never later than 90."
					)
				}}
			</p>
		</div>
		<div class="flex flex-wrap gap-2" data-tour="privacy-actions">
			<Button
				icon-left="lucide-scroll-text"
				:label="t('Privacy notice')"
				:route="{ name: 'PrivacyNotice' }"
			/>
			<Button
				icon-left="lucide-file-user"
				:label="t('See my data')"
				:route="{ name: 'MyData' }"
			/>
			<Button icon-left="lucide-user-lock" :label="t('Ask about my data')" @click="ask" />
			<Button variant="ghost" theme="red" :label="t('Withdraw consent')" @click="withdraw" />
		</div>

		<p v-if="error" role="alert" class="text-sm text-ink-red-4">{{ error }}</p>
		<ul v-else-if="requests?.length" class="flex flex-col">
			<li
				v-for="request in requests"
				:key="request.name"
				class="flex flex-col gap-1 border-b border-outline-gray-1 py-3"
			>
				<div class="flex items-center gap-2">
					<span class="flex-1 text-base font-medium text-ink-gray-8">{{
						request.request_type
					}}</span>
					<Badge
						:label="t(request.status)"
						:theme="REQUEST_STATUS_THEMES[request.status]"
					/>
				</div>
				<p class="text-sm text-ink-gray-6">{{ request.details }}</p>
				<p v-if="request.response" class="text-sm text-ink-gray-8">
					<span class="font-medium">{{ t("Answer:") }}</span> {{ request.response }}
				</p>
				<p class="text-sm text-ink-gray-5">
					Asked {{ formatDate(request.received_on) }}
					<template v-if="!request.closed_on">
						· {{ t("answer due by {0}", formatDate(request.due_by)) }}</template
					>
				</p>
			</li>
		</ul>
	</section>
</template>

<script setup>
// On Account: the privacy notice, requests about one's own data and their answers, and
// withdrawing consent.
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { Badge, Button, dialog, toast } from "frappe-ui";
import { call } from "@/api";
import { boot } from "@/boot";
import { formatDate } from "@/lib/format";
import { t } from "@/lib/i18n";
import { REQUEST_STATUS_THEMES, REQUEST_TYPES } from "@/lib/privacy";
import { notLoaded } from "@/offline/reachability";

const router = useRouter();
const requests = ref(null);
const error = ref("");

async function load() {
	try {
		requests.value = await call("kxcompliance.api.my_privacy_requests");
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("your privacy requests") : err.message;
	}
}

function ask() {
	dialog.prompt({
		title: t("Ask about my data"),
		message: t(
			"A manager answers within 30 days, and never later than 90. Records the law requires are kept even when you ask to erase them."
		),
		confirmLabel: t("Send"),
		fields: [
			{
				name: "request_type",
				label: t("What do you want?"),
				type: "select",
				required: true,
				defaultValue: REQUEST_TYPES[0].value,
				options: REQUEST_TYPES.map(({ label, value }) => ({ label: t(label), value })),
			},
			{ name: "details", label: t("Details"), type: "textarea", required: true },
		],
		onConfirm: async ({ values }) => {
			try {
				await call("kxcompliance.api.raise_privacy_request", values, {
					httpMethod: "POST",
				});
				toast.success(t("Sent. A manager will answer."));
				await load();
			} catch (err) {
				toast.error(err.message);
			}
		},
	});
}

function withdraw() {
	dialog.confirm({
		title: t("Withdraw consent"),
		message: t(
			"You will not be able to use the app until you accept the privacy notice again. Records the law requires are kept."
		),
		confirmLabel: t("Withdraw"),
		theme: "red",
		onConfirm: async () => {
			try {
				await call(
					"kxcompliance.api.withdraw_privacy_consent",
					{},
					{ httpMethod: "POST" }
				);
				boot.privacyNoticeDue = true;
				router.replace({ name: "PrivacyNotice", query: { next: "/" } });
			} catch (err) {
				toast.error(err.message);
			}
		},
	});
}

onMounted(load);
</script>
