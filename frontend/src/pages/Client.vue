<template>
	<AppPageHeader
		:title="clientLabel(client) || 'Client'"
		:parent="clientLogin ? null : { label: 'Clients', route: { name: 'Clients' } }"
	>
		<template #actions>
			<Button
				v-if="client && boot.mayBill && !clientLogin"
				v-bind="isMobile ? { icon: 'lucide-receipt' } : { iconLeft: 'lucide-receipt' }"
				:label="isMobile ? undefined : 'New bill'"
				:aria-label="isMobile ? 'New bill' : undefined"
				:route="{ name: 'NewBill', query: { client: name } }"
			/>
			<Button
				v-if="client && isManager() && !clientLogin"
				v-bind="isMobile ? { icon: 'lucide-pencil' } : { iconLeft: 'lucide-pencil' }"
				:label="isMobile ? undefined : 'Edit'"
				:aria-label="isMobile ? 'Edit' : undefined"
				:route="{ name: 'ClientEdit', params: { name } }"
			/>
			<Dropdown v-if="client && menu.length" :options="menu" align="end">
				<Button variant="ghost" icon="lucide-ellipsis" label="More actions" />
			</Dropdown>
		</template>
	</AppPageHeader>

	<RecordFrame doctype="Compliance Client" :name="name" :facts="client ? keyFacts : []">
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<div v-else-if="!client" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton class="h-6 w-1/2 rounded" />
			<Skeleton class="mt-4 h-32 w-full rounded-lg" />
		</div>

		<template v-else>
			<section class="flex items-start gap-4">
				<img
					v-if="client.logo"
					:src="client.logo"
					:alt="t('{0} logo', clientLabel(client))"
					class="size-14 shrink-0 rounded-lg bg-surface-gray-1 object-contain p-1"
				/>
				<div class="flex min-w-0 flex-col gap-2">
					<div class="flex flex-wrap items-center gap-2">
						<Badge
							:label="client.status"
							:theme="client.status === 'Active' ? 'green' : 'gray'"
							size="md"
						/>
						<span class="text-base" :class="TONE[clientTheme(client)]">{{
							clientAttention(client)
						}}</span>
					</div>
					<p class="text-base text-ink-gray-6">{{ people }}</p>
				</div>
			</section>

			<Tabs :model-value="tab" @update:model-value="tab = $event">
				<TabList class="overflow-x-auto" data-tour="client-tabs">
					<TabTrigger
						value="overview"
						:label="t('Overview')"
						icon-left="lucide-layout-dashboard"
					/>
					<TabTrigger
						value="companies"
						:label="companiesLabel"
						icon-left="lucide-building-2"
					/>
					<TabTrigger
						v-if="mayBill"
						value="billing"
						label="Billing"
						icon-left="lucide-receipt"
					/>
				</TabList>
				<TabPanel
					v-if="mayBill"
					value="billing"
					class="data-[state=inactive]:hidden flex flex-col gap-8 pt-6"
				>
					<ClientAccount :client="name" />
				</TabPanel>
				<TabPanel
					value="overview"
					class="data-[state=inactive]:hidden flex flex-col gap-8 pt-6"
				>
					<section class="flex flex-col gap-3" aria-labelledby="year-heading">
						<div class="flex flex-col gap-0.5">
							<h2 id="year-heading" class="text-base font-semibold text-ink-gray-8">
								{{ t("This financial year") }}
							</h2>
							<p class="text-sm text-ink-gray-5">
								{{
									t(
										"Filings due {0} to {1}; notices, documents and DSCs as of today.",
										formatDate(client.year.from_date),
										formatDate(client.year.to_date)
									)
								}}
							</p>
						</div>
						<dl class="grid grid-cols-2 gap-3 sm:grid-cols-3">
							<div
								v-for="fact in yearFacts(client.year, { client: clientLogin })"
								:key="fact.label"
								class="flex flex-col gap-0.5 rounded-lg bg-surface-gray-1 px-3 py-2.5"
							>
								<dt class="text-sm text-ink-gray-6">{{ fact.label }}</dt>
								<dd class="text-xl font-semibold" :class="FACT_TONE[fact.tone]">
									{{ fact.value }}
								</dd>
								<dd class="text-sm text-ink-gray-5">{{ fact.detail }}</dd>
							</div>
						</dl>
					</section>

					<BillingCard v-if="clientLogin" :client="name" own />

					<section class="flex flex-col gap-1" aria-labelledby="requests-heading">
						<div class="flex items-center justify-between gap-3 pb-2">
							<h2
								id="requests-heading"
								class="text-base font-semibold text-ink-gray-8"
							>
								{{
									clientLogin
										? t("Documents your firm needs")
										: t("Document requests")
								}}
							</h2>
							<Button
								v-if="mayAsk"
								icon-left="lucide-file-up"
								label="Ask for a document"
								@click="asking = true"
							/>
						</div>
						<p v-if="!client.requests.length" class="text-base text-ink-gray-5">
							{{
								clientLogin
									? t("Nothing needed right now.")
									: t("Nothing asked for.")
							}}
						</p>
						<WorkRow
							v-for="request in client.requests"
							:key="request.name"
							:row="requestRow(request, { client: clientLogin })"
						/>
					</section>

					<section class="flex flex-col gap-1" aria-labelledby="open-heading">
						<h2 id="open-heading" class="pb-2 text-base font-semibold text-ink-gray-8">
							{{ t("Open filings") }}
						</h2>
						<p v-if="!client.filings.length" class="text-base text-ink-gray-5">
							{{ t("Nothing open.") }}
						</p>
						<WorkRow
							v-for="filing in client.filings"
							:key="filing.name"
							:row="taskRow(filing)"
						/>
						<Button
							v-if="!clientLogin && client.open > client.filings.length"
							class="mt-2 self-start"
							variant="ghost"
							icon-right="lucide-arrow-right"
							:label="`See all ${client.open} open filings`"
							@click="seeAllFilings"
						/>
					</section>
				</TabPanel>
				<TabPanel
					value="companies"
					class="data-[state=inactive]:hidden flex flex-col gap-8 pt-6"
				>
					<section class="flex flex-col gap-3" aria-labelledby="companies-heading">
						<div class="flex items-center justify-between gap-3">
							<h2
								id="companies-heading"
								class="text-base font-semibold text-ink-gray-8"
							>
								{{ t("Companies") }}
							</h2>
							<Button
								v-if="isManager() && !clientLogin"
								icon-left="lucide-plus"
								label="Add company"
								:route="{ name: 'CompanyNew', query: { client: client.name } }"
							/>
						</div>
						<p v-if="!client.companies.length" class="text-base text-ink-gray-5">
							<template v-if="clientLogin">
								{{ t("Your firm has not linked your companies yet.") }}
							</template>
							<template v-else>No companies yet.</template>
						</p>
						<ul class="flex flex-col">
							<li
								v-for="company in client.companies"
								:key="company.company"
								class="flex items-center gap-3 border-b border-outline-gray-1 py-2.5 last:border-b-0"
							>
								<ScoreBadge :score="company.score.score" />
								<span class="flex min-w-0 flex-1 flex-col">
									<RouterLink
										v-if="isManager() && !clientLogin"
										:to="{
											name: 'Company',
											params: { company: company.company },
										}"
										class="truncate text-base text-ink-gray-8 underline decoration-outline-gray-3 underline-offset-2"
										>{{ company.company }}</RouterLink
									>
									<span v-else class="truncate text-base text-ink-gray-8">{{
										company.company
									}}</span>
									<span class="truncate text-sm text-ink-gray-5">{{
										[
											company.company_type,
											...company.score.reasons.map((reason) => reason.label),
										].join(" · ")
									}}</span>
									<!-- On a phone it goes under the name, which then keeps its room. -->
									<span
										class="text-sm sm:hidden"
										:class="TONE[clientTheme(company)]"
										>{{ clientAttention(company) }}</span
									>
								</span>
								<span
									class="hidden text-sm sm:inline"
									:class="TONE[clientTheme(company)]"
									>{{ clientAttention(company) }}</span
								>
							</li>
						</ul>
					</section>

					<section
						v-if="client.signatures.length"
						class="flex flex-col gap-1"
						aria-labelledby="signatures-heading"
					>
						<h2
							id="signatures-heading"
							class="pb-2 text-base font-semibold text-ink-gray-8"
						>
							Digital signatures
						</h2>
						<WorkRow
							v-for="signature in client.signatures"
							:key="signature.name"
							:row="itemRow({ ...signature, item_type: DSC_TYPE })"
						/>
					</section>

					<section class="flex flex-col gap-1" aria-labelledby="signatories-heading">
						<div class="flex items-center justify-between gap-3 pb-2">
							<h2
								id="signatories-heading"
								class="text-base font-semibold text-ink-gray-8"
							>
								{{ t("Signatories") }}
							</h2>
							<Button
								v-if="mayRecord() && !clientLogin && client.companies.length"
								icon-left="lucide-plus"
								label="Add signatory"
								:route="{
									name: 'SignatoryNew',
									query: { company: client.companies[0].company },
								}"
							/>
						</div>
						<p v-if="!client.signatories.length" class="text-base text-ink-gray-5">
							{{ t("No directors, partners or signatories recorded yet.") }}
						</p>
						<WorkRow
							v-for="signatory in client.signatories"
							:key="signatory.name"
							:row="signatoryRow(signatory)"
						/>
					</section>
				</TabPanel>
			</Tabs>
		</template>
	</RecordFrame>

	<AskDocument
		v-if="mayAsk"
		v-model:open="asking"
		:companies="client.companies.map((row) => row.company)"
		@created="opened"
	/>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { Badge, Button, Dropdown, Skeleton, TabList, TabPanel, TabTrigger, Tabs } from "frappe-ui";
import { RouterLink, useRouter } from "vue-router";
import { chooseClient } from "@/stores/clientFilter";
import { call } from "@/api";
import { boot, isClientLogin, isManager, mayRecord, mayUseDesk } from "@/boot";
import AskDocument from "@/components/AskDocument.vue";
import BillingCard from "@/components/BillingCard.vue";
import ClientAccount from "@/components/ClientAccount.vue";
import ScoreBadge from "@/components/ScoreBadge.vue";
import AppPageHeader from "@/components/AppPageHeader.vue";
import RecordFrame from "@/components/RecordFrame.vue";
import WorkRow from "@/components/WorkRow.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { learnNames, nameOf } from "@/composables/usePeople";
import { useTabQuery } from "@/composables/useTabQuery";
import { clientAttention, clientLabel, clientTheme, yearFacts } from "@/lib/clients";
import { formatDate } from "@/lib/format";
import { t } from "@/lib/i18n";
import { taskRow } from "@/lib/filings";
import { DSC_TYPE, itemRow } from "@/lib/items";
import { requestRow } from "@/lib/requests";
import { signatoryRow } from "@/lib/signatories";
import { deskActions, deskPath } from "@/navigation";
import { notLoaded } from "@/offline/reachability";

const props = defineProps({ name: { type: String, required: true } });

const TONE = {
	red: "font-medium text-ink-red-5",
	amber: "text-ink-amber-5",
	green: "text-ink-gray-6",
};

const FACT_TONE = { red: "text-ink-red-4", amber: "text-ink-amber-4", gray: "text-ink-gray-8" };

const client = ref(null);

// The band across the top: who looks after the client, and how much there is to do.
const keyFacts = computed(() => [
	{
		label: "Relationship manager",
		icon: "lucide-user-round",
		value: nameOf(client.value.relationship_manager),
	},
	{
		label: "Companies",
		icon: "lucide-building-2",
		value: String(client.value.companies.length),
	},
	{
		label: "Open filings",
		icon: "lucide-calendar-check",
		value: String(client.value.open ?? client.value.filings.length),
	},
	{
		label: "Documents asked for",
		icon: "lucide-file-up",
		value: String(client.value.requests.length),
	},
]);
const error = ref("");
const clientLogin = isClientLogin();
const isMobile = useIsMobile();
// The client in tabs: its year and open work, its companies with their people and signatures,
// and, for those who bill, its account.
const mayBill = !clientLogin && boot.mayBill;
const tab = useTabQuery(["overview", "companies", ...(mayBill ? ["billing"] : [])]);
const companiesLabel = computed(() =>
	client.value?.companies.length
		? t("Companies ({0})", client.value.companies.length)
		: t("Companies")
);
const router = useRouter();

// The page lists the soonest open filings; the rest are on Filings, with this client chosen.
function seeAllFilings() {
	chooseClient(props.name);
	router.push({ name: "Filings" });
}
const asking = ref(false);
const mayAsk = computed(
	() =>
		!clientLogin &&
		mayRecord() &&
		client.value?.status !== "Left" &&
		client.value?.companies.length
);
const opened = (request) =>
	router.push({ name: "DocumentRequest", params: { name: request.name } });

const people = computed(() => {
	const manager = client.value.relationship_manager;
	const team = client.value.team.filter((user) => user !== manager).map(nameOf);
	const contact = manager
		? clientLogin
			? `Your contact at the firm: ${nameOf(manager)}`
			: `Managed by ${nameOf(manager)}`
		: "";
	return [contact, team.length && `Team: ${team.join(", ")}`].filter(Boolean).join(" · ");
});

const menu = computed(() => [
	...deskActions("Compliance Client", props.name),
	...(mayUseDesk()
		? [
				{
					label: "Client Summary report",
					icon: "lucide-table",
					onClick: () =>
						(window.location.href = `${deskPath(
							"query-report/Client Summary"
						)}?${new URLSearchParams({ client: props.name })}`),
				},
		  ]
		: []),
]);

async function load() {
	error.value = "";
	try {
		client.value = await call("kxcompliance.api.client_detail", { client: props.name });
		learnNames([client.value.relationship_manager, ...client.value.team]);
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this client", "opened") : err.message;
	}
}

watch(() => props.name, load);
onMounted(load);
</script>
