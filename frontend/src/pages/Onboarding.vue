<template>
	<div class="flex min-h-full flex-col bg-surface-base">
		<div class="mx-auto flex w-full max-w-xl flex-1 flex-col gap-6 px-4 py-8 sm:px-6 sm:py-12">
			<div class="flex flex-col gap-1">
				<p class="text-sm text-ink-gray-5">
					{{ step === "done" ? "All set" : `Step ${stepNumber} of ${steps.length}` }}
				</p>
				<h1 class="text-2xl font-semibold text-ink-gray-9">{{ heading }}</h1>
				<p class="text-base text-ink-gray-6">{{ intro }}</p>
			</div>

			<p
				v-if="error"
				role="alert"
				class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
			>
				{{ error }}
			</p>

			<div
				v-if="options && !options.system_ready"
				class="flex flex-col gap-3 rounded-lg bg-surface-amber-1 px-4 py-3 text-ink-amber-7"
			>
				<p class="text-base">
					The system's own setup (language, currency, financial year) has not been done
					on this site yet. Finish it in the Desk, then come back here.
				</p>
				<Button
					class="self-start"
					variant="solid"
					label="Open the system setup"
					href="/app"
				/>
			</div>

			<div v-else-if="!options && !error" class="flex flex-col gap-3" aria-busy="true">
				<Skeleton class="h-20 w-full rounded-lg" />
				<Skeleton class="h-20 w-full rounded-lg" />
			</div>

			<!-- Who the site is for -->
			<div
				v-else-if="step === 'who'"
				class="flex flex-col gap-3"
				role="radiogroup"
				aria-label="Who is this for"
			>
				<button
					v-for="choice in ACCOUNT_CHOICES"
					:key="choice.value"
					type="button"
					role="radio"
					:aria-checked="answers.account_type === choice.value"
					class="flex items-start gap-3 rounded-lg border px-4 py-4 text-left hover:bg-surface-gray-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4"
					:class="
						answers.account_type === choice.value
							? 'border-outline-gray-5'
							: 'border-outline-gray-2'
					"
					@click="answers.account_type = choice.value"
				>
					<span
						:class="choice.icon"
						class="mt-0.5 size-5 shrink-0 text-ink-gray-7"
						aria-hidden="true"
					/>
					<span class="flex flex-col gap-0.5">
						<span class="text-base font-semibold text-ink-gray-8">{{
							choice.label
						}}</span>
						<span class="text-base text-ink-gray-6">{{ choice.detail }}</span>
					</span>
				</button>
			</div>

			<!-- The firm -->
			<div v-else-if="step === 'firm'" class="flex flex-col gap-4">
				<FormControl
					v-model="answers.firm_name"
					label="Your firm's name"
					placeholder="Rao & Associates"
					description="The app shows it to your team and, later, to your clients."
				/>
			</div>

			<!-- The company -->
			<div v-else-if="step === 'company'" class="flex flex-col gap-4">
				<FormControl
					v-if="answers.account_type === 'CA/CS Firm'"
					v-model="answers.client_name"
					label="Client's name"
					placeholder="Sunrise Group"
					description="The client this company belongs to; a client can own several companies."
					:error="errorFor('client_name')"
				/>
				<TabButtons
					v-if="options.can_create_company && openCompanies.length"
					v-model="companyChoice"
					:options="[
						{ label: 'An existing company', value: 'existing' },
						{ label: 'A new company', value: 'new' },
					]"
				/>
				<FormControl
					v-if="companyChoice === 'new'"
					v-model="answers.new_company"
					label="Company name"
					placeholder="Sunrise Foods Private Limited"
					:error="errorFor('company')"
				/>
				<FormControl
					v-else
					v-model="answers.company"
					type="select"
					label="Company"
					:options="openCompanies"
					placeholder="Choose the company"
					:error="errorFor('company')"
				/>
				<FormControl
					v-model="answers.company_type"
					type="select"
					label="What kind of company"
					:options="options.company_types"
					placeholder="Private Limited, LLP, ..."
					:error="errorFor('company_type')"
				/>
			</div>

			<!-- Registrations -->
			<div v-else-if="step === 'registrations'" class="flex flex-col gap-4">
				<div
					v-for="(row, index) in answers.registrations"
					:key="index"
					class="flex flex-col gap-3 rounded-lg border border-outline-gray-2 p-3"
				>
					<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
						<FormControl
							v-model="row.registration_type"
							type="select"
							label="Registration"
							:options="options.registration_types"
							placeholder="GST, TAN, PF, ..."
						/>
						<FormControl
							v-model="row.registration_number"
							label="Number"
							:placeholder="
								NUMBER_HINTS[row.registration_type] || 'Registration number'
							"
						/>
					</div>
					<FormControl
						v-if="needsState(row)"
						v-model="row.state"
						type="select"
						label="State"
						:options="options.states.filter(Boolean)"
						placeholder="Choose the state"
					/>
					<Button
						class="self-end"
						variant="ghost"
						icon-left="lucide-trash-2"
						label="Remove"
						@click="answers.registrations.splice(index, 1)"
					/>
				</div>
				<Button
					class="self-start"
					icon-left="lucide-plus"
					label="Add a registration"
					@click="addRegistration"
				/>
				<p v-if="registrationError" role="alert" class="text-base text-ink-red-4">
					{{ registrationError }}
				</p>
			</div>

			<!-- People -->
			<div v-else-if="step === 'people'" class="flex flex-col gap-4">
				<FormControl
					v-model="answers.responsible"
					type="select"
					label="Who prepares the filings"
					:options="peopleOptions"
					placeholder="Choose a person"
					:error="errorFor('responsible')"
				/>
				<FormControl
					v-model="answers.reviewer"
					type="select"
					label="Who checks them before they are marked filed"
					:options="peopleOptions"
					placeholder="Choose a person (optional)"
				/>
				<p class="text-sm text-ink-gray-5">
					Each filing can be given to someone else later. People appear here once they
					have a Compliance Manager or Compliance User role.
				</p>
			</div>

			<!-- Done -->
			<div v-else-if="step === 'done'" class="flex flex-col gap-4">
				<div
					class="flex items-start gap-3 rounded-lg bg-surface-green-1 px-4 py-3 text-ink-green-7"
				>
					<span class="lucide-circle-check mt-0.5 size-5 shrink-0" aria-hidden="true" />
					<p class="text-base">
						{{ result.company }} has {{ result.obligations }} recurring filings in its
						calendar; {{ result.tasks }} are due in the coming weeks.
					</p>
				</div>
			</div>

			<div class="mt-auto flex flex-col-reverse gap-2 pt-4 sm:flex-row sm:justify-end">
				<Button
					v-if="stepNumber > 1 && step !== 'done'"
					label="Back"
					:size="buttonSize"
					:disabled="saving"
					@click="back"
				/>
				<Button
					v-if="step === 'done'"
					variant="solid"
					label="Open My Work"
					:size="buttonSize"
					@click="finish"
				/>
				<Button
					v-else-if="options?.system_ready"
					variant="solid"
					:label="step === 'people' ? 'Set up' : 'Continue'"
					:size="buttonSize"
					:loading="saving"
					:disabled="!canContinue"
					@click="next"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { Button, FormControl, Skeleton, TabButtons } from "frappe-ui";
import { call } from "@/api";
import { useIsMobile } from "@/composables/useIsMobile";
import {
	ACCOUNT_CHOICES,
	NUMBER_HINTS,
	onboardingSteps,
	registrationProblem,
	setupAnswers,
	stateFromGstin,
} from "@/lib/onboarding";

const isMobile = useIsMobile();
const buttonSize = computed(() => (isMobile.value ? "md" : "sm"));

const options = ref(null);
const error = ref("");
const saving = ref(false);
const checking = ref(false);
const result = ref(null);
const step = ref("who");
const companyChoice = ref("new");
const answers = reactive({
	account_type: "",
	firm_name: "",
	client_name: "",
	new_company: "",
	company: "",
	company_type: "",
	registrations: [],
	responsible: "",
	reviewer: "",
});

const steps = computed(() => onboardingSteps(answers.account_type));
const stepNumber = computed(() => steps.value.indexOf(step.value) + 1);
const openCompanies = computed(() =>
	(options.value?.companies || [])
		.filter((company) => !company.set_up)
		.map((company) => company.name)
);
const peopleOptions = computed(() =>
	(options.value?.people || []).map((person) => ({
		label: person.full_name || person.name,
		value: person.name,
	}))
);

const HEADINGS = {
	who: ["Who is this for?", "The app sets itself up for how you will use it."],
	firm: ["Your firm", "You will add your clients and their companies next."],
	company: ["The company", "Start with one company; more can be added afterwards."],
	registrations: [
		"Its registrations",
		"GST, TAN, PF, ESI and the rest decide which filings it has. Leave out any it does not hold.",
	],
	people: ["Who looks after the filings", "Reminders and escalations go to these people."],
	done: ["Your calendar is ready", "Filings fall due in My Work as their dates approach."],
};
const heading = computed(() => {
	if (step.value === "company" && answers.account_type === "CA/CS Firm")
		return "Your first client's company";
	return HEADINGS[step.value][0];
});
const intro = computed(() => HEADINGS[step.value][1]);

const REQUIRED = {
	client_name: () => (answers.account_type === "CA/CS Firm" ? answers.client_name : "-"),
	company: () => (companyChoice.value === "new" ? answers.new_company : answers.company),
	company_type: () => answers.company_type,
	responsible: () => answers.responsible,
};
const errorFor = (field) =>
	checking.value && !String(REQUIRED[field]() || "").trim() ? "Needed to continue." : "";

const needsState = (row) => options.value.state_registrations.includes(row.registration_type);
const registrationError = computed(() =>
	checking.value
		? registrationProblem(answers.registrations, options.value.state_registrations)
		: ""
);

const canContinue = computed(() => {
	if (step.value === "who") return Boolean(answers.account_type);
	return !saving.value;
});

// A GSTIN carries its state, so the state is filled in from it unless someone chose one.
watch(
	() =>
		answers.registrations.map((row) => `${row.registration_type}|${row.registration_number}`),
	() => {
		for (const row of answers.registrations) {
			if (row.registration_type.startsWith("GST") && !row.state) {
				row.state = stateFromGstin(row.registration_number);
			}
		}
	}
);

function addRegistration() {
	answers.registrations.push({ registration_type: "", registration_number: "", state: "" });
}

function stepIsComplete() {
	if (step.value === "company")
		return !errorFor("client_name") && !errorFor("company") && !errorFor("company_type");
	if (step.value === "registrations") return !registrationError.value;
	if (step.value === "people") return !errorFor("responsible");
	return true;
}

async function next() {
	checking.value = true;
	if (!stepIsComplete()) return;
	checking.value = false;
	if (step.value !== "people") {
		step.value = steps.value[stepNumber.value];
		return;
	}
	saving.value = true;
	error.value = "";
	try {
		result.value = await call(
			"kxcompliance.api.complete_onboarding",
			{ setup: setupAnswers(answers, companyChoice.value) },
			{ httpMethod: "POST" }
		);
		step.value = "done";
	} catch (err) {
		error.value = err.message;
	} finally {
		saving.value = false;
	}
}

function back() {
	checking.value = false;
	step.value = steps.value[stepNumber.value - 2];
}

// A full load, so the app starts again as a set-up site with the new company in it.
const finish = () => (window.location.href = "/compliance");

onMounted(async () => {
	try {
		options.value = await call("kxcompliance.api.onboarding_options");
		// After ERPNext's own setup there is usually a company already, and it is the one meant.
		if (openCompanies.value.length || !options.value.can_create_company) {
			companyChoice.value = "existing";
			answers.company = openCompanies.value.length === 1 ? openCompanies.value[0] : "";
		}
		addRegistration();
	} catch (err) {
		error.value = err.message;
	}
});
</script>
