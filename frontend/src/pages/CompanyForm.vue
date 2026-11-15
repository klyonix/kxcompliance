<template>
	<AppPageHeader
		:title="company || 'Set up a company'"
		:parent="{ label: 'Companies', route: { name: 'Companies' } }"
	/>

	<RecordFrame doctype="Company Compliance Profile" :name="company">
		<div class="flex flex-col gap-8">
			<p
				v-if="error"
				role="alert"
				class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
			>
				{{ error }}
			</p>
			<div v-else-if="!options" class="flex flex-col gap-3" aria-busy="true">
				<Skeleton class="h-6 w-1/3 rounded" />
				<Skeleton class="h-40 w-full rounded-lg" />
			</div>

			<template v-else>
				<section
					v-if="score"
					class="flex items-start gap-4 rounded-lg border border-outline-gray-1 px-4 py-4"
					aria-labelledby="score-heading"
				>
					<ScoreBadge :score="score.score" />
					<div class="flex min-w-0 flex-1 flex-col gap-1">
						<h2 id="score-heading" class="text-base font-semibold text-ink-gray-8">
							Compliance score {{ score.score }} of 100
						</h2>
						<p v-if="!score.reasons.length" class="text-base text-ink-gray-6">
							Nothing to fix.
						</p>
						<ul v-else class="flex flex-col gap-0.5 text-base text-ink-gray-7">
							<li v-for="reason in score.reasons" :key="reason.key">
								{{ reason.label }} ({{ reason.points }})
							</li>
						</ul>
						<p
							v-if="score.late_fees_so_far"
							class="text-base font-medium text-ink-red-4"
						>
							Late fees building up on overdue filings:
							{{ formatMoney(score.late_fees_so_far) }}
						</p>
					</div>
				</section>

				<Tabs v-model="tab">
					<!-- A phone has no room for the row of tabs: they become a list to choose from. -->
					<FormControl
						v-if="isMobile"
						v-model="tab"
						type="select"
						:options="tabOptions"
						aria-label="Show"
					/>
					<TabList v-else class="overflow-x-auto">
						<TabTrigger
							value="company"
							label="Company"
							icon-left="lucide-building-2"
							data-tour="tab-company"
						/>
						<TabTrigger
							value="registrations"
							label="Registrations"
							icon-left="lucide-id-card"
							data-tour="tab-registrations"
						/>
						<TabTrigger
							v-if="hasAgm"
							value="agm"
							label="AGM dates"
							icon-left="lucide-calendar-days"
							data-tour="tab-agm"
						/>
						<TabTrigger
							v-if="company"
							value="obligations"
							label="Obligations"
							icon-left="lucide-list-checks"
							data-tour="tab-obligations"
						/>
					</TabList>
					<TabPanel value="company" class="flex flex-col gap-8 pt-2 sm:pt-6">
						<section class="flex flex-col gap-4" aria-labelledby="company-heading">
							<h2
								id="company-heading"
								class="text-base font-semibold text-ink-gray-8"
							>
								Company
							</h2>
							<template v-if="!company">
								<TabButtons
									v-if="options.can_create_company"
									v-model="form.mode"
									:options="[
										{ label: 'Already in ERPNext', value: 'existing' },
										{ label: 'New company', value: 'new' },
									]"
								/>
								<FormControl
									v-if="form.mode === 'existing'"
									v-model="form.existing"
									type="select"
									label="Company"
									:options="[
										{ label: 'Choose a company', value: '' },
										...notSetUp,
									]"
								/>
								<FormControl
									v-else
									v-model="form.new_name"
									label="Name of the new company"
									placeholder="Sunrise Foods Private Limited"
								/>
							</template>
							<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
								<FormControl
									v-model="form.company_type"
									type="select"
									label="Kind"
									:options="choices(options.company_types, 'Choose the kind')"
								/>
								<FormControl
									v-if="isFirm"
									v-model="form.client"
									type="select"
									label="Client"
									:options="choices(options.clients, 'No client')"
								/>
								<FormControl
									v-model="form.default_responsible"
									type="select"
									label="Responsible for filings"
									:options="[{ label: 'Choose someone', value: '' }, ...people]"
								/>
								<FormControl
									v-model="form.default_reviewer"
									type="select"
									label="Reviewer"
									:options="[{ label: 'No reviewer', value: '' }, ...people]"
								/>
							</div>
						</section>
					</TabPanel>
					<TabPanel value="registrations" class="flex flex-col gap-8 pt-2 sm:pt-6">
						<section
							class="flex flex-col gap-3"
							aria-labelledby="registrations-heading"
						>
							<div class="flex flex-col gap-0.5">
								<h2
									id="registrations-heading"
									class="text-base font-semibold text-ink-gray-8"
								>
									Registrations
								</h2>
								<p class="text-sm text-ink-gray-5">
									Each registration brings the filings it needs, from the
									obligation library.
								</p>
							</div>
							<div
								v-for="(row, index) in form.registrations"
								:key="index"
								class="flex flex-col gap-2 rounded-lg bg-surface-gray-1 p-3 sm:flex-row sm:items-end"
							>
								<FormControl
									v-model="row.registration_type"
									type="select"
									label="Type"
									:options="choices(options.registration_types)"
									class="sm:w-44"
								/>
								<FormControl
									v-model="row.registration_number"
									label="Number"
									class="sm:flex-1"
								/>
								<FormControl
									v-if="needsState(row)"
									v-model="row.state"
									type="select"
									label="State"
									:options="choices(options.states, 'Choose the state')"
									class="sm:w-48"
								/>
								<Button
									variant="ghost"
									icon="lucide-trash-2"
									label="Remove registration"
									@click="form.registrations.splice(index, 1)"
								/>
							</div>
							<div>
								<Button
									icon-left="lucide-plus"
									label="Add a registration"
									@click="
										form.registrations.push({
											registration_type: 'GST',
											registration_number: '',
											state: '',
										})
									"
								/>
							</div>
						</section>
					</TabPanel>
					<TabPanel value="agm" class="flex flex-col gap-8 pt-2 sm:pt-6">
						<section
							v-if="hasAgm"
							class="flex flex-col gap-3"
							aria-labelledby="agm-heading"
						>
							<div class="flex items-start justify-between gap-3">
								<div class="flex flex-col gap-0.5">
									<h2
										id="agm-heading"
										class="text-base font-semibold text-ink-gray-8"
									>
										AGM dates
									</h2>
									<p class="text-sm text-ink-gray-5">
										When each year's AGM was held. These filings fall due a set
										number of days after it:
										{{ agmFilings.join(", ") || "none now" }}.
									</p>
								</div>
								<Button
									icon-left="lucide-plus"
									label="Add an AGM"
									@click="addAgm"
								/>
							</div>
							<p v-if="!form.agm_dates.length" class="text-base text-ink-gray-5">
								No AGM recorded yet, so those filings have no due date.
							</p>
							<div
								v-for="(row, index) in form.agm_dates"
								:key="index"
								class="grid grid-cols-[1fr_1fr_auto] items-end gap-2"
							>
								<FormControl
									v-model="row.financial_year_end"
									type="date"
									:format="pickerFormat()"
									label="Year ended"
								/>
								<FormControl
									v-model="row.agm_date"
									type="date"
									:format="pickerFormat()"
									label="AGM held on"
								/>
								<Button
									variant="ghost"
									icon="lucide-trash-2"
									:label="`Remove the AGM for the year ended ${
										row.financial_year_end || ''
									}`"
									@click="form.agm_dates.splice(index, 1)"
								/>
							</div>
						</section>
					</TabPanel>
					<TabPanel value="obligations" class="flex flex-col gap-8 pt-2 sm:pt-6">
						<section
							v-if="company"
							class="flex flex-col gap-3"
							aria-labelledby="obligations-heading"
						>
							<div class="flex flex-col gap-0.5">
								<h2
									id="obligations-heading"
									class="text-base font-semibold text-ink-gray-8"
								>
									Obligations
								</h2>
								<p class="text-sm text-ink-gray-5">
									The filings the company makes. Untick one that does not apply;
									set who handles each.
								</p>
							</div>
							<div
								v-for="row in form.obligations"
								:key="row.name"
								class="flex flex-col gap-2 border-b border-outline-gray-1 py-2.5 last:border-b-0 sm:flex-row sm:items-center"
							>
								<div class="flex min-w-0 flex-1 items-start gap-3">
									<FormControl
										v-model="row.is_active"
										type="checkbox"
										:aria-label="`${row.obligation_template} applies`"
									/>
									<span class="flex min-w-0 flex-col">
										<span
											class="truncate text-base"
											:class="
												row.is_active
													? 'text-ink-gray-8'
													: 'text-ink-gray-5 line-through'
											"
											>{{ row.obligation_template }}</span
										>
										<span class="truncate text-sm text-ink-gray-5">{{
											[
												row.law,
												row.frequency,
												row.registration_number || row.state,
											]
												.filter(Boolean)
												.join(" · ")
										}}</span>
									</span>
								</div>
								<FormControl
									v-model="row.responsible"
									type="select"
									:options="[{ label: 'Company default', value: '' }, ...people]"
									:aria-label="`Responsible for ${row.obligation_template}`"
									class="sm:w-56"
								/>
							</div>
						</section>
					</TabPanel>
				</Tabs>
			</template>
		</div>
	</RecordFrame>

	<div
		v-if="options"
		class="sticky bottom-0 z-10 mt-auto border-t border-outline-gray-1 bg-surface-base"
	>
		<div
			class="mx-auto flex w-full flex-col-reverse gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-end sm:px-6"
			:class="recordWidth(company)"
		>
			<p v-if="saveError" role="alert" class="text-sm text-ink-red-4 sm:mr-auto">
				{{ saveError }}
			</p>
			<Button
				variant="solid"
				:label="company ? 'Save' : 'Set up company'"
				:loading="saving"
				@click="save"
			/>
		</div>
	</div>
</template>

<script setup>
// Set a company up for compliance, or change its kind, client, people, registrations and
// which obligations apply.
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
	Button,
	FormControl,
	Skeleton,
	TabButtons,
	TabList,
	TabPanel,
	TabTrigger,
	Tabs,
	toast,
} from "frappe-ui";
import { call } from "@/api";
import { boot } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import RecordFrame from "@/components/RecordFrame.vue";
import ScoreBadge from "@/components/ScoreBadge.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { useTabQuery } from "@/composables/useTabQuery";
import { formatMoney, pickerFormat } from "@/lib/format";
import { personOptions } from "@/lib/people";
import { recordWidth } from "@/lib/records";
import { notLoaded } from "@/offline/reachability";

const props = defineProps({ company: { type: String, default: "" } });
// The company's details in tabs; the open one is kept in the address.
const tab = useTabQuery(["company", "registrations", "agm", "obligations"]);
const isMobile = useIsMobile();
// The tabs a phone offers in its list: AGM dates and obligations once the company is set up.
const tabOptions = computed(() =>
	[
		{ label: "Company", value: "company" },
		{ label: "Registrations", value: "registrations" },
		hasAgm.value && { label: "AGM dates", value: "agm" },
		props.company && { label: "Obligations", value: "obligations" },
	].filter(Boolean)
);

const route = useRoute();
const router = useRouter();
const options = ref(null);
const notSetUpList = ref([]);
const error = ref("");
const saveError = ref("");
const saving = ref(false);
const score = ref(null);
const form = reactive({
	mode: "existing",
	existing: "",
	new_name: "",
	company_type: "",
	client: "",
	default_responsible: "",
	default_reviewer: "",
	registrations: [],
	obligations: [],
	agm_dates: [],
});
const agmFilings = ref([]);
// AGM dates apply once the company is set up and has filings that fall due after its AGM.
const hasAgm = computed(
	() => Boolean(props.company) && (agmFilings.value.length > 0 || form.agm_dates.length > 0)
);

// A new row for the latest year not yet recorded: years end on 31 March.
function addAgm() {
	const years = form.agm_dates.map((row) => Number(String(row.financial_year_end).slice(0, 4)));
	const today = new Date();
	const lastEnded = today.getMonth() >= 3 ? today.getFullYear() : today.getFullYear() - 1;
	const year = years.length ? Math.max(...years) + 1 : lastEnded;
	form.agm_dates.push({
		financial_year_end: `${Math.min(year, lastEnded)}-03-31`,
		agm_date: "",
	});
}

const isFirm = boot.accountType === "CA/CS Firm";
const people = computed(() => personOptions(options.value?.people || []));
const notSetUp = computed(() => notSetUpList.value.map((name) => ({ label: name, value: name })));
const choices = (values, empty) => [
	...(empty ? [{ label: empty, value: "" }] : []),
	...values.map((value) => ({ label: value, value })),
];
const needsState = (row) => options.value.state_registrations.includes(row.registration_type);

async function save() {
	saveError.value = "";
	const name = props.company || (form.mode === "new" ? form.new_name.trim() : form.existing);
	if (!name) {
		saveError.value = "Choose the company, or give the name of a new one.";
		return;
	}
	saving.value = true;
	try {
		const result = await call(
			"kxcompliance.api.save_company",
			{
				company: name,
				new_company: !props.company && form.mode === "new",
				values: {
					company_type: form.company_type,
					client: form.client || null,
					default_responsible: form.default_responsible,
					default_reviewer: form.default_reviewer || null,
					registrations: form.registrations,
					...(props.company ? { agm_dates: form.agm_dates } : {}),
					obligations: form.obligations.map((row) => ({
						name: row.name,
						is_active: row.is_active ? 1 : 0,
						responsible: row.responsible || null,
						reviewer: row.reviewer || null,
					})),
				},
			},
			{ httpMethod: "POST" }
		);
		const added = result.obligations
			? ` ${result.obligations} obligations and ${result.tasks} filings added.`
			: "";
		toast.success((props.company ? "Company saved." : "Company set up.") + added);
		if (props.company) await load();
		else router.replace({ name: "Company", params: { company: result.company } });
	} catch (err) {
		saveError.value = err.isNetwork
			? "The company did not reach the server. Try again when you are back online."
			: err.message;
	} finally {
		saving.value = false;
	}
}

async function load() {
	error.value = "";
	try {
		options.value = await call("kxcompliance.api.company_form_options");
		notSetUpList.value = options.value.not_set_up;
		if (props.company) {
			const detail = await call("kxcompliance.api.company_detail", {
				company: props.company,
			});
			score.value = detail.score;
			agmFilings.value = detail.agm_filings || [];
			Object.assign(form, {
				company_type: detail.company_type || "",
				client: detail.client || "",
				default_responsible: detail.default_responsible || "",
				default_reviewer: detail.default_reviewer || "",
				registrations: detail.registrations.map((row) => ({
					...row,
					state: row.state || "",
				})),
				agm_dates: (detail.agm_dates || []).map((row) => ({ ...row })),
				obligations: detail.obligations.map((row) => ({
					...row,
					is_active: Boolean(row.is_active),
					responsible: row.responsible || "",
					reviewer: row.reviewer || "",
				})),
			});
		} else {
			form.existing = notSetUpList.value.includes(route.query.company)
				? route.query.company
				: "";
			form.client = route.query.client || "";
		}
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this company", "opened") : err.message;
	}
}

watch(() => props.company, load);
onMounted(load);
</script>
