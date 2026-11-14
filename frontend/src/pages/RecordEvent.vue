<template>
	<AppPageHeader title="Record an event" />

	<div class="mx-auto flex w-full max-w-xl flex-col gap-5 px-4 py-6 sm:px-6">
		<template v-if="recorded">
			<div
				class="flex items-start gap-3 rounded-lg bg-surface-green-1 px-4 py-3 text-ink-green-7"
			>
				<span class="lucide-circle-check mt-0.5 size-5 shrink-0" aria-hidden="true" />
				<div class="flex flex-col gap-0.5">
					<p class="text-base font-semibold">{{ form.event_type }} recorded</p>
					<p class="text-base">{{ recordedSummary }}</p>
				</div>
			</div>
			<ul v-if="filings.length" class="flex flex-col">
				<li
					v-for="filing in filings"
					:key="filing.name"
					class="flex items-center gap-3 border-b border-outline-gray-1 py-2.5 last:border-b-0"
				>
					<span
						class="lucide-calendar-check size-4 text-ink-gray-5"
						aria-hidden="true"
					/>
					<RouterLink
						:to="{ name: 'ComplianceTask', params: { name: filing.name } }"
						class="flex-1 text-base text-ink-gray-8 hover:underline"
						>{{ filing.obligation_template }}</RouterLink
					>
					<span class="text-sm text-ink-gray-6"
						>Due {{ formatDate(filing.effective_due_date) }}</span
					>
				</li>
			</ul>
			<div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
				<Button label="Record another" :size="buttonSize" @click="reset" />
				<Button
					variant="solid"
					label="Back to Filings"
					:size="buttonSize"
					:route="{ name: 'Filings' }"
				/>
			</div>
		</template>

		<form v-else class="flex flex-col gap-5" novalidate @submit.prevent="save">
			<p class="text-base text-ink-gray-6">
				Record a change as soon as it happens, such as a director appointed or shares
				allotted. The filings it calls for are created with their due dates.
			</p>

			<p
				v-if="!isConnected()"
				class="flex items-center gap-2 rounded-lg bg-surface-amber-1 px-3 py-2 text-base text-ink-amber-7"
			>
				<span class="lucide-cloud-off size-4 shrink-0" aria-hidden="true" />
				Recording an event needs a connection to the server.
			</p>

			<FormControl
				v-if="boot.companies.length > 1"
				v-model="form.company"
				type="select"
				label="Company"
				:options="boot.companies"
				required
				:error="errorFor('company')"
			/>
			<FormControl
				v-model="form.event_type"
				type="select"
				label="What changed"
				:options="eventTypes.map((type) => type.name)"
				placeholder="Choose the event"
				required
				:description="chosenType?.description"
				:error="errorFor('event_type')"
			/>
			<FormControl
				v-model="form.event_date"
				type="date"
				:format="pickerFormat()"
				label="When it happened"
				placeholder="Pick a date"
				required
				:error="errorFor('event_date')"
			/>
			<FormControl
				v-model="form.description"
				type="textarea"
				label="What happened"
				placeholder="Asha Rao appointed as an additional director"
				required
				:rows="3"
				:error="errorFor('description')"
			/>
			<FormControl
				v-model="form.reference"
				label="Reference"
				placeholder="Board meeting of 10 Nov 2026, resolution 4"
			/>

			<p v-if="formError" role="alert" class="text-base text-ink-red-4">{{ formError }}</p>

			<div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
				<Button
					label="Cancel"
					:size="buttonSize"
					:route="{ name: 'Filings' }"
					:disabled="saving"
				/>
				<Button
					type="submit"
					variant="solid"
					label="Record event"
					:size="buttonSize"
					:loading="saving"
					:disabled="!isConnected()"
				/>
			</div>
		</form>
	</div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { Button, FormControl, toast } from "frappe-ui";
import { createDoc, getList, readMethod } from "@/api";
import { boot } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { formatDate, pickerFormat } from "@/lib/format";
import { isConnected } from "@/offline/outbox";

const isMobile = useIsMobile();
const buttonSize = computed(() => (isMobile.value ? "md" : "sm"));

// Today on this device's calendar, as YYYY-MM-DD (toISOString would give the UTC date).
const today = () => {
	const now = new Date();
	const pad = (value) => String(value).padStart(2, "0");
	return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
};
const blank = () => ({
	company: boot.defaultCompany || boot.companies[0] || "",
	event_type: "",
	event_date: today(),
	description: "",
	reference: "",
});

const form = reactive(blank());
const eventTypes = ref([]);
const saving = ref(false);
const checking = ref(false);
const formError = ref("");
const recorded = ref(null);
const filings = ref([]);

const chosenType = computed(() => eventTypes.value.find((type) => type.name === form.event_type));
const recordedSummary = computed(() => {
	if (!filings.value.length) return "No filing follows this event for this company.";
	const count = filings.value.length;
	return `${count} filing${count === 1 ? " is" : "s are"} now due:`;
});

const REQUIRED = {
	company: "Pick the company.",
	event_type: "Choose what changed.",
	event_date: "Pick the date it happened.",
	description: "Say what happened.",
};
const errorFor = (field) =>
	checking.value && !String(form[field] || "").trim() ? REQUIRED[field] : "";

async function save() {
	checking.value = true;
	formError.value = "";
	if (Object.keys(REQUIRED).some((field) => errorFor(field))) return;
	saving.value = true;
	try {
		const event = await createDoc("Compliance Event", {
			...form,
			description: form.description.trim(),
		});
		recorded.value = event.name;
		filings.value = await readMethod("Compliance Event", event.name, "filings");
		toast.success("Event recorded");
	} catch (err) {
		formError.value = err.message;
	} finally {
		saving.value = false;
	}
}

function reset() {
	Object.assign(form, blank());
	recorded.value = null;
	filings.value = [];
	checking.value = false;
}

onMounted(async () => {
	try {
		eventTypes.value = (
			await getList("Compliance Event Type", {
				fields: ["name", "description"],
				orderBy: "name asc",
				limit: 100,
			})
		).rows;
	} catch (err) {
		formError.value = err.message;
	}
});
</script>
