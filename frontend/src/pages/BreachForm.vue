<template>
	<AppPageHeader
		:title="name ? form.title || 'Data breach' : 'Record a breach'"
		:parent="{ label: 'Data breaches', route: { name: 'Breaches' } }"
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
			<Skeleton v-else-if="loading" class="h-48 w-full rounded-lg" />

			<template v-else>
				<p
					v-if="deadline"
					class="rounded-lg px-3 py-2 text-base"
					:class="
						deadline.includes('late')
							? 'bg-surface-red-1 text-ink-red-4'
							: 'bg-surface-amber-1 text-ink-amber-7'
					"
				>
					{{ deadline }} ({{ formatDateTime(saved.board_due_by) }}).
				</p>

				<section class="flex flex-col gap-4" aria-labelledby="breach-heading">
					<h2 id="breach-heading" class="text-base font-semibold text-ink-gray-8">
						What happened
					</h2>
					<FormControl
						v-model="form.title"
						label="Title"
						placeholder="Laptop with client files stolen"
						:disabled="!editable"
					/>
					<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
						<FormControl
							v-model="form.discovered_on"
							type="datetime"
							:format="`${pickerFormat()} h:mm a`"
							label="Discovered on"
							description="The Board is told within 72 hours of this."
							:disabled="!editable"
						/>
						<FormControl
							v-model="form.people_affected"
							type="number"
							label="People affected"
							:disabled="!editable"
						/>
					</div>
					<FormControl
						v-model="form.description"
						type="textarea"
						label="What happened"
						:disabled="!editable"
					/>
					<FormControl
						v-model="form.data_affected"
						type="textarea"
						label="Personal data affected"
						placeholder="Names, PAN and mobile numbers of the directors of 12 clients"
						:disabled="!editable"
					/>
					<FormControl
						v-model="form.measures_taken"
						type="textarea"
						label="What was done about it"
						:disabled="!editable"
					/>
				</section>

				<section
					class="flex flex-col gap-4"
					aria-labelledby="reported-heading"
					data-tour="breach-reported"
				>
					<div class="flex flex-col gap-0.5">
						<h2 id="reported-heading" class="text-base font-semibold text-ink-gray-8">
							Who was told
						</h2>
						<p class="text-sm text-ink-gray-5">
							The Data Protection Board within 72 hours, and each person affected
							without delay, in plain words: what happened, what it means for them
							and what they can do.
						</p>
					</div>
					<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
						<FormControl
							v-model="form.board_reported_on"
							type="datetime"
							:format="`${pickerFormat()} h:mm a`"
							label="Board told on"
							:disabled="!editable"
						/>
						<FormControl
							v-model="form.people_informed_on"
							type="datetime"
							:format="`${pickerFormat()} h:mm a`"
							label="People affected told on"
							:disabled="!editable"
						/>
					</div>
				</section>
			</template>
		</div>
	</RecordFrame>

	<div
		v-if="!loading && !error && editable"
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
				:label="name ? 'Save' : 'Record breach'"
				:loading="saving"
				@click="save"
			/>
		</div>
	</div>
</template>

<script setup>
// A personal data breach: what happened, and when the Board and the people affected were told.
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { Button, FormControl, Skeleton, toast } from "frappe-ui";
import { createDoc, getDoc, updateDoc } from "@/api";
import { isManager } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import RecordFrame from "@/components/RecordFrame.vue";
import { formatDateTime, pickerFormat } from "@/lib/format";
import { boardDeadline } from "@/lib/privacy";
import { recordWidth } from "@/lib/records";
import { notLoaded } from "@/offline/reachability";

const DOCTYPE = "Personal Data Breach";
const FIELDS = [
	"title",
	"discovered_on",
	"people_affected",
	"description",
	"data_affected",
	"measures_taken",
	"board_reported_on",
	"people_informed_on",
];
const props = defineProps({ name: { type: String, default: "" } });

const router = useRouter();
const editable = isManager();
const form = reactive(Object.fromEntries(FIELDS.map((field) => [field, ""])));
const saved = ref({});
const loading = ref(Boolean(props.name));
const error = ref("");
const saveError = ref("");
const saving = ref(false);
const deadline = computed(() => boardDeadline(saved.value));

function show(doc) {
	saved.value = doc;
	for (const field of FIELDS) form[field] = doc[field] ?? "";
}

async function save() {
	saveError.value = "";
	if (!form.title.trim() || !form.discovered_on || !form.description.trim()) {
		saveError.value = "Give it a title, when it was discovered and what happened.";
		return;
	}
	saving.value = true;
	const values = Object.fromEntries(
		FIELDS.map((field) => [
			field,
			typeof form[field] === "string" ? form[field].trim() || null : form[field],
		])
	);
	values.people_affected = Number(form.people_affected) || 0;
	try {
		if (props.name) {
			show(await updateDoc(DOCTYPE, props.name, values));
			toast.success("Saved");
		} else {
			const doc = await createDoc(DOCTYPE, values);
			// The page may stay as it is under its new address, so it shows the saved breach.
			show(doc);
			toast.success("Breach recorded");
			router.replace({ name: "Breach", params: { name: doc.name } });
		}
	} catch (err) {
		saveError.value = err.isNetwork
			? "The breach did not reach the server. Try again when you are back online."
			: err.message;
	} finally {
		saving.value = false;
	}
}

onMounted(async () => {
	if (!props.name) return;
	try {
		show(await getDoc(DOCTYPE, props.name));
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this breach", "opened") : err.message;
	} finally {
		loading.value = false;
	}
});
</script>
