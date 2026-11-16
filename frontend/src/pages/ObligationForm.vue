<template>
	<AppPageHeader
		:title="name || 'New obligation'"
		:parent="{ label: 'Obligation library', route: { name: 'ObligationLibrary' } }"
	/>

	<RecordFrame :doctype="DOCTYPE" :name="name">
		<div class="flex flex-col gap-8">
			<p
				v-if="error"
				role="alert"
				class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
			>
				{{ error }}
			</p>
			<div v-else-if="!ready" class="flex flex-col gap-3" aria-busy="true">
				<Skeleton class="h-6 w-1/3 rounded" />
				<Skeleton class="h-48 w-full rounded-lg" />
			</div>

			<template v-else>
				<!-- A standard obligation: its rules come from the app, read-only here. -->
				<section
					v-if="standard"
					class="flex flex-col gap-4"
					aria-labelledby="rules-heading"
				>
					<div class="flex flex-col gap-0.5">
						<h2 id="rules-heading" class="text-base font-semibold text-ink-gray-8">
							Rules
						</h2>
						<p class="text-sm text-ink-gray-5">
							A standard obligation: each update keeps these rules in line with the
							law. When a date is extended, add a due-date extension; for a different
							rule, add your own obligation.
						</p>
					</div>
					<dl
						class="grid grid-cols-1 gap-x-6 gap-y-3 text-base sm:grid-cols-[10rem_1fr]"
					>
						<template v-for="fact in facts" :key="fact.label">
							<dt class="text-ink-gray-5">{{ fact.label }}</dt>
							<dd class="text-ink-gray-8">{{ fact.value }}</dd>
						</template>
					</dl>
				</section>

				<!-- A firm's own obligation: every rule is theirs to set. -->
				<template v-else>
					<section class="flex flex-col gap-4" aria-labelledby="what-heading">
						<h2 id="what-heading" class="text-base font-semibold text-ink-gray-8">
							What it is
						</h2>
						<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
							<FormControl
								v-if="!name"
								v-model="form.template_name"
								class="sm:col-span-2"
								label="Name"
								placeholder="Trade Licence Return (BBMP)"
							/>
							<FormControl
								v-model="form.law"
								type="select"
								label="Law"
								:options="choices(options.law)"
							/>
							<FormControl v-model="form.form" label="Form" placeholder="Form 5" />
							<FormControl
								v-model="form.authority"
								label="Authority"
								placeholder="Labour Department"
							/>
							<FormControl
								v-model="form.source"
								label="Source"
								placeholder="Section or notification"
							/>
						</div>
					</section>

					<section class="flex flex-col gap-4" aria-labelledby="when-heading">
						<h2 id="when-heading" class="text-base font-semibold text-ink-gray-8">
							When it is due
						</h2>
						<FormControl
							v-model="form.due_after_event"
							type="checkbox"
							label="Due a number of days after the AGM or a company event"
						/>
						<div
							v-if="form.due_after_event"
							class="grid grid-cols-1 gap-4 sm:grid-cols-2"
						>
							<FormControl
								v-model="form.event_type"
								type="select"
								label="After"
								:options="[
									{ label: 'The AGM', value: '' },
									...choices(options.event_types),
								]"
							/>
							<FormControl
								v-model="form.days_after_event"
								type="number"
								label="Days after"
							/>
						</div>
						<template v-else>
							<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
								<FormControl
									v-model="form.frequency"
									type="select"
									label="How often"
									:options="
										choices(
											options.frequency.filter(
												(value) => value !== 'Per Event'
											)
										)
									"
								/>
								<FormControl
									v-model="form.period_basis"
									type="select"
									label="Periods follow"
									:options="choices(options.period_basis)"
								/>
								<FormControl
									v-model="form.months_after_period"
									type="number"
									label="Months after the period"
									description="0 is the period's last month, 1 the month after it."
								/>
								<FormControl
									v-model="form.due_day"
									type="number"
									label="Due day"
									description="31 means the month's last day."
								/>
							</div>
							<p class="text-sm text-ink-gray-6">
								Due {{ dueText(form.months_after_period, form.due_day) }}.
							</p>

							<div class="flex flex-col gap-2">
								<div class="flex items-center justify-between gap-3">
									<h3 class="text-base font-medium text-ink-gray-8">
										Exceptions
									</h3>
									<Button
										icon-left="lucide-plus"
										label="Add an exception"
										@click="addException"
									/>
								</div>
								<p class="text-sm text-ink-gray-5">
									A different date for periods ending in a given month, such as
									March.
								</p>
								<div
									v-for="(row, index) in form.overrides"
									:key="index"
									class="grid grid-cols-[1fr_1fr_1fr_auto] items-end gap-2"
								>
									<FormControl
										v-model="row.period_end_month"
										type="select"
										label="Ending in"
										:options="MONTHS"
									/>
									<FormControl
										v-model="row.months_after_period"
										type="number"
										label="Months after"
									/>
									<FormControl
										v-model="row.due_day"
										type="number"
										label="Due day"
									/>
									<Button
										icon="lucide-trash-2"
										variant="ghost"
										:aria-label="`Remove exception ${index + 1}`"
										@click="form.overrides.splice(index, 1)"
									/>
								</div>
							</div>
						</template>
					</section>

					<section class="flex flex-col gap-4" aria-labelledby="who-heading">
						<div class="flex flex-col gap-0.5">
							<h2 id="who-heading" class="text-base font-semibold text-ink-gray-8">
								Who it applies to
							</h2>
							<p class="text-sm text-ink-gray-5">
								Leave a list empty for every kind of company or every state.
							</p>
						</div>
						<fieldset class="flex flex-col gap-2">
							<legend class="mb-2 text-sm text-ink-gray-6">Kinds of company</legend>
							<div class="grid grid-cols-1 gap-2 sm:grid-cols-3">
								<FormControl
									v-for="type in options.company_types"
									:key="type"
									v-model="form.company_types[type]"
									type="checkbox"
									:label="type"
								/>
							</div>
						</fieldset>
						<FormControl
							v-model="form.registration_type"
							type="select"
							label="Only for companies registered for"
							:options="[
								{ label: 'Any company', value: '' },
								...choices(options.registration_type),
							]"
						/>
						<details class="rounded-lg border border-outline-gray-1 px-3 py-2">
							<summary class="cursor-pointer text-base text-ink-gray-8">
								States
								<span class="text-ink-gray-5">· {{ statesSummary }}</span>
							</summary>
							<div class="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
								<FormControl
									v-for="state in options.states"
									:key="state"
									v-model="form.states[state]"
									type="checkbox"
									:label="state"
								/>
							</div>
						</details>
					</section>

					<section class="flex flex-col gap-4" aria-labelledby="how-heading">
						<h2 id="how-heading" class="text-base font-semibold text-ink-gray-8">
							How it is filed
						</h2>
						<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
							<FormControl
								v-model="form.requires_proof"
								type="checkbox"
								label="Proof of filing needed"
							/>
							<FormControl
								v-model="form.requires_review"
								type="checkbox"
								label="A second person reviews it"
							/>
							<FormControl
								v-model="form.requires_payment"
								type="checkbox"
								label="Involves a payment"
							/>
							<FormControl
								v-model="form.add_by_default"
								type="checkbox"
								label="Ticked for matching companies at setup"
							/>
						</div>
						<FormControl
							v-model="form.reminder_days"
							label="Remind (days before the due date)"
							placeholder="7, 2, 0"
						/>
						<FormControl
							v-model="form.description"
							type="textarea"
							label="Notes"
							:rows="3"
						/>
					</section>
				</template>

				<FormControl
					v-if="!standard || own.may_edit_obligation"
					v-model="form.is_active"
					type="checkbox"
					label="In use: the calendar makes filings for it"
				/>
				<p v-else class="text-sm text-ink-gray-5">
					To stop filings for it, switch it off for each company on the company's page.
				</p>

				<section class="flex flex-col gap-4" aria-labelledby="late-heading">
					<div class="flex flex-col gap-0.5">
						<h2 id="late-heading" class="text-base font-semibold text-ink-gray-8">
							Filing late
						</h2>
						<p class="text-sm text-ink-gray-5">{{ figuresNote }}</p>
					</div>
					<div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
						<FormControl
							v-model="form.late_fee_per_day"
							type="number"
							label="Late fee a day (₹)"
						/>
						<FormControl
							v-model="form.late_fee_flat"
							type="number"
							label="One-off late fee (₹)"
						/>
						<FormControl
							v-model="form.late_fee_cap"
							type="number"
							label="At most (₹; 0 for no cap)"
						/>
						<FormControl
							v-model="form.interest_percent"
							type="number"
							label="Interest (% a year)"
						/>
					</div>
					<FormControl
						v-model="form.cap_at_tax"
						type="checkbox"
						label="The late fee cannot exceed the tax"
					/>
					<FormControl
						v-model="form.penalty_rule"
						type="textarea"
						label="The rule in words"
						:rows="3"
					/>
					<div v-if="standard && own.set_by_firm">
						<Button
							label="Use the library's figures"
							:loading="restoring"
							@click="useLibraryFigures"
						/>
					</div>
				</section>

				<section
					v-if="name"
					class="flex flex-col gap-3"
					aria-labelledby="extensions-heading"
				>
					<div class="flex items-center justify-between gap-3">
						<h2
							id="extensions-heading"
							class="text-base font-semibold text-ink-gray-8"
						>
							Due-date extensions
						</h2>
						<Button
							icon-left="lucide-calendar-clock"
							label="Extend a due date"
							:route="{ name: 'ExtensionNew', query: { template: name } }"
						/>
					</div>
					<p v-if="!extensions.length" class="text-sm text-ink-gray-5">None yet.</p>
					<ul v-else class="flex flex-col">
						<li v-for="extension in extensions" :key="extension.name">
							<RouterLink
								:to="{ name: 'Extension', params: { name: extension.name } }"
								class="flex items-center gap-3 rounded-lg px-3 py-2.5 hover:bg-surface-gray-2"
							>
								<span class="flex min-w-0 flex-1 flex-col">
									<span class="truncate text-base text-ink-gray-8">{{
										periodsText(
											extension.periods_ending_from,
											extension.periods_ending_to
										)
									}}</span>
									<span class="truncate text-sm text-ink-gray-5">{{
										extension.notification_reference
									}}</span>
								</span>
								<span class="text-sm text-ink-gray-6">{{
									formatDate(extension.new_due_date)
								}}</span>
							</RouterLink>
						</li>
					</ul>
				</section>
			</template>
		</div>
	</RecordFrame>

	<div
		v-if="ready"
		class="sticky bottom-0 z-10 mt-auto border-t border-outline-gray-1 bg-surface-base"
	>
		<div
			class="mx-auto flex w-full flex-col-reverse gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-end sm:px-6"
			:class="recordWidth(name)"
		>
			<p v-if="saveError" role="alert" class="text-sm text-ink-red-4 sm:mr-auto">
				{{ saveError }}
			</p>
			<Button
				variant="solid"
				:label="name ? 'Save' : 'Add obligation'"
				:loading="saving"
				@click="save"
			/>
		</div>
	</div>
</template>

<script setup>
// One obligation of the library. A standard one shows its rules and lets the firm switch it off
// and set its own late-filing figures; the firm's own ones are fully editable.
import { computed, onMounted, reactive, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { Button, FormControl, Skeleton, toast } from "frappe-ui";
import { call, createDoc, getDoc, getList, updateDoc } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import RecordFrame from "@/components/RecordFrame.vue";
import { formatDate } from "@/lib/format";
import { daysText, parseDays } from "@/lib/itemTypes";
import { EXTENSION_FIELDS, dueText, periodsText, ruleSummary, stateList } from "@/lib/obligations";
import { recordWidth } from "@/lib/records";
import { notLoaded } from "@/offline/reachability";

const DOCTYPE = "Compliance Obligation Template";
const MONTHS = [
	"Jan",
	"Feb",
	"Mar",
	"Apr",
	"May",
	"Jun",
	"Jul",
	"Aug",
	"Sep",
	"Oct",
	"Nov",
	"Dec",
].map((label, index) => ({ label, value: String(index + 1) }));

const props = defineProps({ name: { type: String, default: "" } });

const router = useRouter();
const ready = ref(false);
const error = ref("");
const saveError = ref("");
const saving = ref(false);
const restoring = ref(false);
const options = ref(null);
const doc = ref({});
// A standard obligation's figures as the firm uses them (kxcompliance.api.obligation_figures).
const own = ref({ figures: {}, set_by_firm: false, may_edit_obligation: true });
const extensions = ref([]);
const form = reactive({
	template_name: "",
	law: "Other",
	form: "",
	authority: "",
	source: "",
	due_after_event: false,
	event_type: "",
	days_after_event: 30,
	frequency: "Monthly",
	period_basis: "Financial Year",
	months_after_period: 1,
	due_day: 20,
	overrides: [],
	company_types: {},
	registration_type: "",
	states: {},
	requires_proof: true,
	requires_review: false,
	requires_payment: false,
	add_by_default: true,
	reminder_days: "7, 2, 0",
	description: "",
	is_active: true,
	late_fee_per_day: 0,
	late_fee_flat: 0,
	late_fee_cap: 0,
	cap_at_tax: false,
	interest_percent: 0,
	penalty_rule: "",
});

const standard = computed(() => Boolean(doc.value.is_standard));
const choices = (values) => values.map((value) => ({ label: value, value }));
const sentence = (text) => text.charAt(0).toUpperCase() + text.slice(1);
const ticked = (map) => Object.keys(map).filter((key) => map[key]);
const statesSummary = computed(() => {
	const states = ticked(form.states);
	if (!states.length) return "every state";
	return states.length === 1 ? states[0] : `${states.length} states`;
});
const figuresNote = computed(() => {
	if (!standard.value)
		return "Used for the penalty estimate on filings and the compliance score.";
	if (own.value.set_by_firm) return "Your own figures: updates keep them.";
	if (!doc.value.penalty_checked_on)
		return "From the library, not yet checked by a chartered accountant. Changing them makes them yours.";
	return `From the library, checked on ${formatDate(
		doc.value.penalty_checked_on
	)}. Changing them makes them yours.`;
});

// What a standard obligation's rules say, in words.
const facts = computed(() => {
	const rules = doc.value;
	const list = (rows, field) => rows.map((row) => row[field]);
	const needs = [
		rules.requires_proof && "proof of filing",
		rules.requires_review && "a second person's review",
		rules.requires_payment && "a payment",
	].filter(Boolean);
	const states = stateList(rules.states);
	return [
		{ label: "Law", value: rules.law },
		{ label: "Form", value: rules.form || "-" },
		{ label: "Authority", value: rules.authority || "-" },
		{ label: "Due", value: ruleSummary(rules) },
		...(rules.overrides || []).map((row) => ({
			label: `Ending in ${MONTHS[row.period_end_month - 1]?.label}`,
			value: `Due ${dueText(row.months_after_period, row.due_day)}`,
		})),
		{
			label: "Kinds of company",
			value: list(rules.company_types || [], "company_type").join(", ") || "Every kind",
		},
		...(rules.registration_type
			? [{ label: "Registered for", value: rules.registration_type }]
			: []),
		{ label: "States", value: states.length ? states.join(", ") : "Every state" },
		{ label: "Needs", value: needs.length ? sentence(needs.join(", ")) : "Nothing extra" },
		{
			label: "Reminders",
			value: rules.reminders?.length ? `${daysText(rules.reminders)} days before` : "None",
		},
		{ label: "Source", value: rules.source || "-" },
		{
			label: "Checked by a CA",
			value: rules.checked_on ? formatDate(rules.checked_on) : "Not yet",
		},
	];
});

function addException() {
	form.overrides.push({ period_end_month: "3", months_after_period: 1, due_day: 31 });
}

const number = (value) => Number(value) || 0;

function figures() {
	return {
		late_fee_per_day: number(form.late_fee_per_day),
		late_fee_flat: number(form.late_fee_flat),
		late_fee_cap: number(form.late_fee_cap),
		cap_at_tax: form.cap_at_tax ? 1 : 0,
		interest_percent: number(form.interest_percent),
		penalty_rule: form.penalty_rule,
	};
}

// The figures as the form shows them, from the obligation or the firm's own.
function figuresForm(source) {
	return {
		late_fee_per_day: source.late_fee_per_day || 0,
		late_fee_flat: source.late_fee_flat || 0,
		late_fee_cap: source.late_fee_cap || 0,
		cap_at_tax: Boolean(source.cap_at_tax),
		interest_percent: source.interest_percent || 0,
		penalty_rule: source.penalty_rule || "",
	};
}

const figuresChanged = () =>
	JSON.stringify(figures()) !==
	JSON.stringify({
		...figuresForm(own.value.figures),
		cap_at_tax: own.value.figures.cap_at_tax ? 1 : 0,
		late_fee_per_day: number(own.value.figures.late_fee_per_day),
		late_fee_flat: number(own.value.figures.late_fee_flat),
		late_fee_cap: number(own.value.figures.late_fee_cap),
		interest_percent: number(own.value.figures.interest_percent),
	});

// A standard obligation's figures are the firm's own record, not the obligation's (which keeps
// the library's); its In Use switch is on the obligation, for those who may change it.
async function saveStandard() {
	if (own.value.may_edit_obligation && form.is_active !== Boolean(doc.value.is_active)) {
		fill(await updateDoc(DOCTYPE, props.name, { is_active: form.is_active ? 1 : 0 }));
	}
	if (figuresChanged()) {
		own.value = await call(
			"kxcompliance.api.save_obligation_figures",
			{ template: props.name, figures: figures() },
			{ httpMethod: "POST" }
		);
	}
	Object.assign(form, figuresForm(own.value.figures));
}

function values() {
	return {
		is_active: form.is_active ? 1 : 0,
		...figures(),
		law: form.law,
		form: form.form,
		authority: form.authority,
		source: form.source,
		due_after_event: form.due_after_event ? 1 : 0,
		event_type: form.due_after_event ? form.event_type || null : null,
		days_after_event: form.due_after_event ? number(form.days_after_event) : 0,
		frequency: form.frequency,
		period_basis: form.period_basis,
		months_after_period: number(form.months_after_period),
		due_day: number(form.due_day),
		overrides: form.due_after_event
			? []
			: form.overrides.map((row) => ({
					period_end_month: number(row.period_end_month),
					months_after_period: number(row.months_after_period),
					due_day: number(row.due_day),
			  })),
		company_types: ticked(form.company_types).map((company_type) => ({ company_type })),
		registration_type: form.registration_type || null,
		states: ticked(form.states).join("\n"),
		requires_proof: form.requires_proof ? 1 : 0,
		requires_review: form.requires_review ? 1 : 0,
		requires_payment: form.requires_payment ? 1 : 0,
		add_by_default: form.add_by_default ? 1 : 0,
		reminders: parseDays(form.reminder_days).map((days) => ({ days_before: days })),
		description: form.description,
	};
}

async function save() {
	saveError.value = "";
	if (!props.name && !form.template_name.trim()) {
		saveError.value = "Give the obligation a name.";
		return;
	}
	saving.value = true;
	try {
		if (props.name && standard.value) {
			await saveStandard();
			toast.success("Obligation saved");
			return;
		}
		const saved = props.name
			? await updateDoc(DOCTYPE, props.name, values())
			: await createDoc(DOCTYPE, { template_name: form.template_name.trim(), ...values() });
		toast.success(props.name ? "Obligation saved" : "Obligation added");
		if (props.name) fill(saved);
		else router.replace({ name: "Obligation", params: { name: saved.name } });
	} catch (err) {
		saveError.value = err.isNetwork
			? "The obligation did not reach the server. Try again when you are back online."
			: err.message;
	} finally {
		saving.value = false;
	}
}

async function useLibraryFigures() {
	restoring.value = true;
	saveError.value = "";
	try {
		own.value = await call(
			"kxcompliance.api.use_library_figures",
			{ template: props.name },
			{ httpMethod: "POST" }
		);
		Object.assign(form, figuresForm(own.value.figures));
		toast.success("Back to the library's figures");
	} catch (err) {
		saveError.value = err.message;
	} finally {
		restoring.value = false;
	}
}

const flags = (values) => Object.fromEntries(values.map((value) => [value, true]));

function fill(template) {
	doc.value = template;
	Object.assign(form, {
		law: template.law,
		form: template.form || "",
		authority: template.authority || "",
		source: template.source || "",
		due_after_event: Boolean(template.due_after_event),
		event_type: template.event_type || "",
		days_after_event: template.days_after_event || 0,
		frequency: template.frequency,
		period_basis: template.period_basis,
		months_after_period: template.months_after_period || 0,
		due_day: template.due_day || 0,
		overrides: (template.overrides || []).map((row) => ({
			period_end_month: String(row.period_end_month),
			months_after_period: row.months_after_period || 0,
			due_day: row.due_day,
		})),
		company_types: flags((template.company_types || []).map((row) => row.company_type)),
		registration_type: template.registration_type || "",
		states: flags(stateList(template.states)),
		requires_proof: Boolean(template.requires_proof),
		requires_review: Boolean(template.requires_review),
		requires_payment: Boolean(template.requires_payment),
		add_by_default: Boolean(template.add_by_default),
		reminder_days: daysText(template.reminders || []),
		description: template.description || "",
		is_active: Boolean(template.is_active),
		...figuresForm(template.is_standard ? own.value.figures : template),
	});
}

onMounted(async () => {
	try {
		options.value = await call("kxcompliance.api.obligation_form_options");
		if (props.name) {
			const [template, rows, figuresInUse] = await Promise.all([
				getDoc(DOCTYPE, props.name),
				getList("Compliance Due Date Extension", {
					fields: EXTENSION_FIELDS,
					filters: [["obligation_template", "=", props.name]],
					orderBy: "periods_ending_to desc",
					limit: 50,
				}),
				call("kxcompliance.api.obligation_figures", { template: props.name }),
			]);
			own.value = figuresInUse;
			fill(template);
			extensions.value = rows.rows;
		}
		ready.value = true;
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this obligation", "opened") : err.message;
	}
});
</script>
