<template>
	<AppPageHeader :title="name ? `Edit ${name}` : 'New client'" :parent="parent" />

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-6 sm:px-6">
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<div v-else-if="!ready" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton class="h-6 w-1/3 rounded" />
			<Skeleton class="h-40 w-full rounded-lg" />
		</div>

		<template v-else>
			<Tabs v-model="tab">
				<!-- A phone has no room for the row of tabs: they become a list to choose from. -->
				<FormControl
					v-if="isMobile"
					v-model="tab"
					type="select"
					:options="TABS"
					aria-label="Show"
				/>
				<TabList v-else class="overflow-x-auto">
					<TabTrigger
						v-for="option in TABS"
						:key="option.value"
						:value="option.value"
						:label="option.label"
						:icon-left="option.icon"
					/>
				</TabList>
				<TabPanel
					value="details"
					class="data-[state=inactive]:hidden flex flex-col gap-8 pt-2 sm:pt-6"
				>
					<section class="flex flex-col gap-4" aria-labelledby="client-heading">
						<h2 id="client-heading" class="text-base font-semibold text-ink-gray-8">
							Client
						</h2>
						<LogoField
							v-if="name"
							v-model="form.logo"
							label="The client's logo, on its page and statements"
							:alt="`${name}'s logo`"
							doctype="Compliance Client"
							:docname="name"
						/>
						<FormControl
							v-if="!name"
							v-model="form.client_name"
							label="Name"
							placeholder="Sunrise Group"
							:error="
								checking && !form.client_name.trim()
									? 'Give the client a name'
									: ''
							"
						/>
						<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
							<FormControl
								v-model="form.client_kind"
								type="select"
								label="Kind"
								:options="KINDS"
							/>
							<FormControl
								v-if="name"
								v-model="form.status"
								type="select"
								label="Status"
								:options="STATUSES"
							/>
							<FormControl
								v-model="form.relationship_manager"
								type="select"
								label="Relationship manager"
								:options="[{ label: 'None', value: '' }, ...peopleOptions]"
								description="Told, with the managers, when this client's work is overdue."
							/>
							<FormControl
								v-model="form.contact_email"
								type="email"
								label="Contact email"
								placeholder="accounts@client.example.com"
								description="Without a login, the client is asked for documents and reminded here, and can reply with the file."
							/>
							<FormControl v-model="form.contact_phone" label="Contact phone" />
						</div>
						<FormControl
							v-model="form.licence_check"
							type="checkbox"
							label="Check their customers' and suppliers' licences"
							description="Sales and purchases of this client's companies are checked against your licence rules before they are saved."
						/>
					</section>

					<section class="flex flex-col gap-3" aria-labelledby="team-heading">
						<div class="flex flex-col gap-0.5">
							<h2 id="team-heading" class="text-base font-semibold text-ink-gray-8">
								Team
							</h2>
							<p class="text-sm text-ink-gray-5">
								The firm's people who work on this client see all its companies.
							</p>
						</div>
						<ul v-if="form.team.length" class="flex flex-col">
							<li
								v-for="user in form.team"
								:key="user"
								class="flex items-center gap-3 border-b border-outline-gray-1 py-2 last:border-b-0"
							>
								<span class="min-w-0 flex-1 truncate text-base text-ink-gray-8">{{
									nameOf(user)
								}}</span>
								<Button
									variant="ghost"
									icon="lucide-x"
									:label="`Take ${nameOf(user)} off the team`"
									@click="
										form.team = form.team.filter((member) => member !== user)
									"
								/>
							</li>
						</ul>
						<FormControl
							v-if="addablePeople.length"
							:model-value="''"
							type="select"
							:options="[
								{ label: 'Add someone to the team', value: '' },
								...addablePeople,
							]"
							aria-label="Add someone to the team"
							@update:model-value="(user) => user && form.team.push(user)"
						/>
					</section>
				</TabPanel>
				<TabPanel
					value="logins"
					class="data-[state=inactive]:hidden flex flex-col gap-8 pt-2 sm:pt-6"
				>
					<section class="flex flex-col gap-3" aria-labelledby="logins-heading">
						<div class="flex flex-col gap-0.5">
							<h2
								id="logins-heading"
								class="text-base font-semibold text-ink-gray-8"
							>
								Client logins
							</h2>
							<p class="text-sm text-ink-gray-5">
								People at the client who may sign in to see their companies and
								upload documents. Each is emailed a link to set a password when
								saved.
							</p>
						</div>
						<div
							v-for="(login, index) in form.logins"
							:key="index"
							class="flex flex-col gap-2 rounded-lg bg-surface-gray-1 p-3 sm:flex-row sm:items-end"
						>
							<FormControl
								v-model="login.full_name"
								label="Name"
								class="sm:flex-1"
							/>
							<FormControl
								v-model="login.email"
								type="email"
								label="Email"
								class="sm:flex-1"
								:disabled="Boolean(login.user)"
							/>
							<div class="flex items-center gap-2 sm:pb-1">
								<FormControl
									v-model="login.enabled"
									type="checkbox"
									label="Login on"
								/>
								<Button
									variant="ghost"
									icon="lucide-trash-2"
									label="Remove login"
									@click="form.logins.splice(index, 1)"
								/>
							</div>
						</div>
						<div>
							<Button
								icon-left="lucide-plus"
								label="Add a login"
								@click="
									form.logins.push({ full_name: '', email: '', enabled: true })
								"
							/>
						</div>
					</section>
				</TabPanel>
				<TabPanel
					value="billing"
					class="data-[state=inactive]:hidden flex flex-col gap-8 pt-2 sm:pt-6"
				>
					<section class="flex flex-col gap-4" aria-labelledby="billing-heading">
						<div class="flex flex-col gap-0.5">
							<h2
								id="billing-heading"
								class="text-base font-semibold text-ink-gray-8"
							>
								Billing
							</h2>
							<p class="text-sm text-ink-gray-5">
								Used for each company of the client that has no billing details of
								its own (on the company's Billing tab). GST follows the state
								against the firm's.
							</p>
						</div>
						<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
							<FormControl
								v-model="form.gstin"
								label="GSTIN"
								placeholder="27AAACA1234F1Z5"
								description="Its state is read from it."
							/>
							<FormControl
								v-model="form.billing_state"
								type="select"
								label="State"
								description="Only when the client has no GSTIN."
								:disabled="Boolean(form.gstin.trim())"
								:options="[
									{ label: 'Choose', value: '' },
									...states.map((state) => ({ label: state, value: state })),
								]"
							/>
						</div>
						<FormControl
							v-model="form.billing_email"
							type="email"
							label="Billing email"
							description="Bills are emailed here; else to the contact email."
						/>
						<FormControl
							v-model="form.billing_address"
							type="textarea"
							label="Billing address"
							:rows="3"
						/>
					</section>

					<section class="flex flex-col gap-4" aria-labelledby="fees-heading">
						<div class="flex flex-col gap-0.5">
							<h2 id="fees-heading" class="text-base font-semibold text-ink-gray-8">
								Rates
							</h2>
							<p class="text-sm text-ink-gray-5">
								The client pays its rate card's rates, the default card's if it has
								none, and its own rates below in their place.
							</p>
						</div>
						<p
							v-if="fees?.unbilled.length"
							class="rounded-lg bg-surface-gray-2 px-3 py-2 text-base text-ink-gray-7"
						>
							{{ unbilledLine }}
						</p>
						<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
							<FormControl
								v-model="form.rate_card"
								type="select"
								label="Rate card"
								:options="[
									{
										label: defaultCard
											? `Default (${defaultCard})`
											: 'Default',
										value: '',
									},
									...rateCards.map((card) => ({
										label: card.title,
										value: card.name,
									})),
								]"
							/>
							<FormControl
								v-model="form.billing_from"
								type="date"
								:format="pickerFormat()"
								label="Recurring charges from"
								description="Monthly, quarterly and yearly charges are billed from here."
							/>
							<FormControl
								v-if="fees?.companies?.length > 1"
								v-model="form.recurring_company"
								type="select"
								label="Bill recurring charges to"
								:options="[
									{ label: `${fees.companies[0]} (the first)`, value: '' },
									...fees.companies.map((name) => ({
										label: name,
										value: name,
									})),
								]"
								description="The company whose bills carry the recurring charges."
							/>
						</div>
						<div class="flex flex-col gap-1.5">
							<span class="text-xs text-ink-gray-5">Own rates</span>
							<RateLines
								v-model="form.own_rates"
								empty="None: the card's rates apply."
							/>
						</div>
					</section>
				</TabPanel>
				<TabPanel
					value="notes"
					class="data-[state=inactive]:hidden flex flex-col gap-8 pt-2 sm:pt-6"
				>
					<section class="flex flex-col gap-3" aria-labelledby="notes-heading">
						<h2 id="notes-heading" class="text-base font-semibold text-ink-gray-8">
							Notes
						</h2>
						<FormControl
							v-model="form.notes"
							type="textarea"
							:rows="3"
							placeholder="For the firm only; clients do not see these."
						/>
					</section>
				</TabPanel>
			</Tabs>
		</template>
	</div>

	<div
		v-if="ready"
		class="sticky bottom-0 z-10 mt-auto border-t border-outline-gray-1 bg-surface-base"
	>
		<div
			class="mx-auto flex w-full max-w-3xl flex-col-reverse gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-end sm:px-6"
		>
			<p v-if="saveError" role="alert" class="text-sm text-ink-red-4 sm:mr-auto">
				{{ saveError }}
			</p>
			<Button label="Cancel" @click="goBack(router, parent.route)" />
			<Button
				variant="solid"
				:label="name ? 'Save' : 'Add client'"
				:loading="saving"
				@click="save"
			/>
		</div>
	</div>
</template>

<script setup>
// Add a client, or change one: its details, the firm's team on it and the client's own logins.
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import {
	Button,
	FormControl,
	Skeleton,
	TabList,
	TabPanel,
	TabTrigger,
	Tabs,
	toast,
} from "frappe-ui";
import { call, createDoc, getDoc, getList, updateDoc } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import LogoField from "@/components/LogoField.vue";
import RateLines from "@/components/RateLines.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { learnNames, nameOf } from "@/composables/usePeople";
import { useTabQuery } from "@/composables/useTabQuery";
import { money, ratesProblem, ratesToSend } from "@/lib/billing";
import { pickerFormat } from "@/lib/format";
import { personOptions } from "@/lib/people";
import { goBack } from "@/navigation";
import { notLoaded } from "@/offline/reachability";

// The form in tabs by what each part is about; the open one is kept in the address.
const TABS = [
	{ label: "Details", value: "details", icon: "lucide-user-round" },
	{ label: "Logins", value: "logins", icon: "lucide-key-round" },
	{ label: "Billing", value: "billing", icon: "lucide-receipt" },
	{ label: "Notes", value: "notes", icon: "lucide-notebook-pen" },
];
const isMobile = useIsMobile();
const tab = useTabQuery(TABS.map((option) => option.value));

const props = defineProps({ name: { type: String, default: "" } });

const KINDS = ["Business Group", "Individual"].map((value) => ({ label: value, value }));
const STATUSES = ["Active", "On Hold", "Left"].map((value) => ({ label: value, value }));

const router = useRouter();
const people = ref([]);
const ready = ref(false);
const error = ref("");
const saveError = ref("");
const states = ref([]);
const fees = ref(null);
// The firm's rate cards to choose from, and the default one a client without a card pays.
const rateCards = ref([]);
const defaultCard = computed(() => rateCards.value.find((card) => card.is_default)?.title || "");
// What the client would be billed for its filings now.
const unbilledLine = computed(() => {
	const count = fees.value.unbilled.length;
	return `${count} filed ${count === 1 ? "return" : "returns"} not billed yet: ${money(
		fees.value.unbilled_total
	)}.`;
});
const saving = ref(false);
const checking = ref(false);
const form = reactive({
	client_name: "",
	client_kind: "Business Group",
	status: "Active",
	relationship_manager: "",
	contact_email: "",
	contact_phone: "",
	licence_check: false,
	logo: "",
	gstin: "",
	billing_state: "",
	billing_email: "",
	billing_address: "",
	rate_card: "",
	billing_from: "",
	recurring_company: "",
	own_rates: [],
	team: [],
	logins: [],
	notes: "",
});

const parent = computed(() =>
	props.name
		? { label: props.name, route: { name: "Client", params: { name: props.name } } }
		: { label: "Clients", route: { name: "Clients" } }
);
const peopleOptions = computed(() => personOptions(people.value));
const addablePeople = computed(() =>
	peopleOptions.value.filter((option) => !form.team.includes(option.value))
);

function values() {
	return {
		client_kind: form.client_kind,
		relationship_manager: form.relationship_manager || null,
		contact_email: form.contact_email.trim() || null,
		contact_phone: form.contact_phone.trim() || null,
		licence_check: form.licence_check ? 1 : 0,
		logo: form.logo || null,
		gstin: form.gstin.trim() || null,
		billing_state: form.billing_state || null,
		billing_email: form.billing_email.trim() || null,
		billing_address: form.billing_address.trim() || null,
		rate_card: form.rate_card || null,
		billing_from: form.billing_from || null,
		recurring_company: form.recurring_company || null,
		own_rates: ratesToSend(form.own_rates),
		team: form.team.map((user) => ({ user })),
		logins: form.logins.map((login) => ({
			full_name: login.full_name.trim(),
			email: login.email.trim(),
			enabled: login.enabled ? 1 : 0,
		})),
		notes: form.notes,
	};
}

async function save() {
	checking.value = true;
	saveError.value = "";
	// A problem shows on its own tab, so that tab is opened.
	if (!props.name && !form.client_name.trim()) {
		tab.value = "details";
		return;
	}
	const priceProblem = ratesProblem(form.own_rates);
	if (priceProblem) {
		tab.value = "billing";
		saveError.value = priceProblem;
		return;
	}
	saving.value = true;
	try {
		const saved = props.name
			? await updateDoc("Compliance Client", props.name, {
					...values(),
					status: form.status,
			  })
			: await createDoc("Compliance Client", {
					client_name: form.client_name.trim(),
					...values(),
			  });
		toast.success(props.name ? "Client saved" : "Client added");
		router.replace({ name: "Client", params: { name: saved.name } });
	} catch (err) {
		saveError.value = err.isNetwork
			? "The client did not reach the server. Try again when you are back online."
			: err.message;
	} finally {
		saving.value = false;
	}
}

onMounted(async () => {
	try {
		const [found, billing, cards] = await Promise.all([
			call("kxcompliance.api.people_options"),
			// The states to bill in; a firm's managers open this form, as they set billing up.
			call("kxcompliance.api.billing_setup").catch(() => ({ states: [] })),
			getList("Rate Card", {
				fields: ["name", "title", "is_default"],
				orderBy: "title asc",
				limit: 200,
			}).catch(() => ({ rows: [] })),
		]);
		people.value = found;
		states.value = billing.states;
		rateCards.value = cards.rows;
		if (props.name) {
			fees.value = await call("kxcompliance.api.client_fees", { client: props.name }).catch(
				() => null
			);
		}
		learnNames(people.value.map((person) => person.name));
		if (props.name) {
			const client = await getDoc("Compliance Client", props.name);
			Object.assign(form, {
				client_kind: client.client_kind || "Business Group",
				status: client.status || "Active",
				relationship_manager: client.relationship_manager || "",
				contact_email: client.contact_email || "",
				contact_phone: client.contact_phone || "",
				licence_check: Boolean(client.licence_check),
				logo: client.logo || "",
				gstin: client.gstin || "",
				billing_state: client.billing_state || "",
				billing_email: client.billing_email || "",
				billing_address: client.billing_address || "",
				rate_card: client.rate_card || "",
				billing_from: client.billing_from || "",
				recurring_company: client.recurring_company || "",
				own_rates: (client.own_rates || []).map((row) => ({
					kind: row.kind,
					obligation_template: row.obligation_template || "",
					service: row.service || "",
					unit: row.unit,
					amount: row.amount,
					sac_code: row.sac_code || "",
				})),
				team: client.team.map((row) => row.user),
				logins: client.logins.map((row) => ({
					full_name: row.full_name,
					email: row.email,
					enabled: Boolean(row.enabled),
					user: row.user,
				})),
				notes: client.notes || "",
			});
		}
		ready.value = true;
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this client", "opened") : err.message;
	}
});
</script>
