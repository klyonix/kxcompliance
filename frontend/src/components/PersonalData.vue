<template>
	<div class="flex flex-col gap-6">
		<div class="flex flex-wrap items-center justify-between gap-2">
			<p class="text-sm text-ink-gray-5">
				{{ t("As of {0}", formatDateTime(data.made_on)) }}
			</p>
			<Button icon-left="lucide-download" :label="t('Download')" @click="download" />
		</div>

		<section class="flex flex-col gap-2" aria-labelledby="data-person">
			<h2 id="data-person" class="text-base font-semibold text-ink-gray-8">
				{{ t("Login") }}
			</h2>
			<dl class="grid grid-cols-1 gap-x-6 gap-y-2 text-base sm:grid-cols-[10rem_1fr]">
				<template v-for="row in personRows" :key="row.label">
					<dt class="text-ink-gray-5">{{ row.label }}</dt>
					<dd class="break-words text-ink-gray-8">{{ row.value || "—" }}</dd>
				</template>
			</dl>
		</section>

		<section
			v-if="data.records.length"
			class="flex flex-col gap-2"
			aria-labelledby="data-records"
		>
			<h2 id="data-records" class="text-base font-semibold text-ink-gray-8">
				{{ t("Records that name you") }}
			</h2>
			<ul class="flex flex-col">
				<li
					v-for="row in data.records"
					:key="row.doctype"
					class="flex justify-between gap-4 border-b border-outline-gray-1 py-2 text-base"
				>
					<span class="text-ink-gray-7">{{ t(row.label) }}</span>
					<span class="text-ink-gray-8">{{ row.count }}</span>
				</li>
			</ul>
		</section>

		<section
			v-if="data.signatory.length"
			class="flex flex-col gap-2"
			aria-labelledby="data-signatory"
		>
			<h2 id="data-signatory" class="text-base font-semibold text-ink-gray-8">
				{{ t("As a signatory") }}
			</h2>
			<ul class="flex flex-col">
				<li
					v-for="(row, index) in data.signatory"
					:key="index"
					class="flex flex-col gap-0.5 border-b border-outline-gray-1 py-2 text-base"
				>
					<span class="text-ink-gray-8">
						{{ row.full_name }} · {{ row.designation }} · {{ row.company }}
					</span>
					<span class="text-sm text-ink-gray-6">
						{{
							[
								row.din && `DIN ${row.din}`,
								row.pan && `PAN ${row.pan}`,
								row.email,
								row.mobile,
							]
								.filter(Boolean)
								.join(" · ")
						}}
					</span>
				</li>
			</ul>
		</section>

		<section class="flex flex-col gap-2" aria-labelledby="data-activity">
			<h2 id="data-activity" class="text-base font-semibold text-ink-gray-8">
				{{ t("Consent, requests and activity") }}
			</h2>
			<ul class="flex flex-col gap-1 text-base text-ink-gray-7">
				<li v-for="consent in data.consents" :key="consent.accepted_on">
					{{
						consent.withdrawn_on
							? t(
									"Accepted the privacy notice (version {0}) on {1}, withdrawn on {2}",
									consent.notice_version,
									formatDate(consent.accepted_on),
									formatDate(consent.withdrawn_on)
							  )
							: t(
									"Accepted the privacy notice (version {0}) on {1}",
									consent.notice_version,
									formatDate(consent.accepted_on)
							  )
					}}
				</li>
				<li v-for="request in data.requests" :key="request.name">
					{{
						t(
							"{0}, asked on {1}: {2}",
							t(request.request_type),
							formatDate(request.received_on),
							t(request.status)
						)
					}}
				</li>
				<li>{{ t("Reminder emails sent to you: {0}", data.emails_sent) }}</li>
				<li>{{ t("Times you signed in: {0}", data.sign_ins) }}</li>
				<li v-if="data.client_logins.length">
					{{ t("Client logins: {0}", data.client_logins.length) }}
				</li>
			</ul>
		</section>
	</div>
</template>

<script setup>
// What the app holds about one person (kxcompliance.kx_compliance.personal_data.summary), read
// by the person on Account, or by a manager answering their request; downloadable as a file.
import { computed } from "vue";
import { Button } from "frappe-ui";
import { formatDate, formatDateTime } from "@/lib/format";
import { t } from "@/lib/i18n";

const props = defineProps({ data: { type: Object, required: true } });

const personRows = computed(() => {
	const person = props.data.person;
	return [
		{ label: t("Name"), value: person.name },
		{ label: t("Email"), value: person.email },
		{ label: t("Mobile"), value: person.mobile },
		{ label: t("Roles"), value: person.roles.join(", ") },
		{ label: t("Photo"), value: person.has_photo ? t("Yes") : t("No") },
		{ label: t("Since"), value: formatDate(person.since) },
		{ label: t("Last signed in"), value: formatDateTime(person.last_sign_in) },
	];
});

function download() {
	const blob = new Blob([JSON.stringify(props.data, null, 1)], { type: "application/json" });
	const link = document.createElement("a");
	link.href = URL.createObjectURL(blob);
	link.download = `personal-data-${String(props.data.made_on).slice(0, 10)}.json`;
	link.click();
	URL.revokeObjectURL(link.href);
}
</script>
