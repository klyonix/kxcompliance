<template>
	<section class="flex flex-col gap-3" aria-labelledby="details-heading">
		<h2 id="details-heading" class="text-base font-semibold text-ink-gray-8">
			{{ heading }}
		</h2>
		<dl class="grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2">
			<div
				v-for="entry in shown"
				:key="entry.key"
				class="flex min-w-0 flex-col gap-0.5"
				:class="{ 'sm:col-span-2': entry.wide }"
			>
				<dt class="text-sm text-ink-gray-5">{{ entry.label }}</dt>
				<dd>
					<!-- The field being changed: Enter or leaving it saves, Escape puts it back. -->
					<div
						v-if="editing === entry.field"
						ref="editor"
						class="flex flex-col gap-1.5"
						@keydown.esc.prevent="cancel"
					>
						<FormControl
							v-if="entry.control === 'note'"
							v-model="draft"
							type="textarea"
							:rows="4"
							:aria-label="entry.label"
							:disabled="saving"
						/>
						<FormControl
							v-else-if="entry.control === 'date'"
							:model-value="draft"
							type="date"
							:format="pickerFormat()"
							:aria-label="entry.label"
							:disabled="saving"
							@update:model-value="(value) => saveNow(value)"
						/>
						<FormControl
							v-else-if="entry.control === 'select' || entry.control === 'person'"
							:model-value="draft"
							type="select"
							:options="entry.options"
							:aria-label="entry.label"
							:disabled="saving"
							@update:model-value="(value) => saveNow(value)"
						/>
						<FormControl
							v-else
							v-model="draft"
							:aria-label="entry.label"
							:disabled="saving"
							@keydown.enter.prevent="save"
							@blur="save"
						/>
						<p v-if="error" role="alert" class="text-sm text-ink-red-4">{{ error }}</p>
						<div class="flex items-center gap-2">
							<Button
								v-if="entry.control === 'note'"
								size="sm"
								variant="solid"
								label="Save"
								:loading="saving"
								@click="save"
							/>
							<Button
								size="sm"
								variant="ghost"
								label="Cancel"
								:disabled="saving"
								@mousedown.prevent
								@click="cancel"
							/>
						</div>
					</div>
					<button
						v-else-if="entry.editable"
						type="button"
						class="group -mx-2 flex w-[calc(100%+1rem)] items-start gap-2 rounded px-2 py-1 text-left hover:bg-surface-gray-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4"
						:aria-label="`Change ${entry.label}`"
						@click="start(entry)"
					>
						<span
							class="min-w-0 flex-1 break-words text-base"
							:class="[
								entry.value ? 'text-ink-gray-8' : 'text-ink-gray-4',
								{ 'whitespace-pre-line': entry.control === 'note' },
							]"
							>{{ entry.value || "Add" }}</span
						>
						<!-- Always there on a phone; on a computer it shows when pointed at. -->
						<span
							class="lucide-pencil mt-1 size-3.5 shrink-0 text-ink-gray-5 sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-visible:opacity-100"
							aria-hidden="true"
						/>
					</button>
					<span
						v-else
						class="block break-words py-1 text-base text-ink-gray-8"
						:class="{ 'whitespace-pre-line': entry.control === 'note' }"
						>{{ entry.value }}</span
					>
				</dd>
			</div>
		</dl>
		<!-- Empty fields wait behind this, so a record shows what it holds first. -->
		<Button
			v-if="empty.length"
			class="self-start"
			variant="ghost"
			:icon-left="showEmpty ? 'lucide-chevron-up' : 'lucide-plus'"
			:label="showEmpty ? 'Hide empty fields' : `Fill in more (${empty.length})`"
			:aria-expanded="showEmpty"
			@click="showEmpty = !showEmpty"
		/>
	</section>
</template>

<script setup>
// A record's details, each changed where it is shown: click it, change it, and it is saved. The
// server says which fields the app may change; the others only show. Empty fields show only to
// those who may fill them in, behind "Fill in more". Saving refuses a change if the record was changed by someone else
// since it was opened, and the page then shows the record as it is now.
import { computed, nextTick, onMounted, ref } from "vue";
import { Button, FormControl } from "frappe-ui";
import { call, saveChanges } from "@/api";
import { nameOf } from "@/composables/usePeople";
import {
	changeFor,
	controlFor,
	editValue,
	mayChangeField,
	readValue,
	selectOptions,
} from "@/lib/editing";
import { pickerFormat } from "@/lib/format";
import { personOptions } from "@/lib/people";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, required: true },
	doc: { type: Object, required: true },
	// [{ field, label?, show?(doc), when?(doc), wide? }], in the order shown. `show` writes a value
	// the page's own way; `when` leaves a detail out of records it does not apply to.
	details: { type: Array, required: true },
	mayEdit: { type: Boolean, default: false },
	heading: { type: String, default: "Details" },
});
const emit = defineEmits(["saved"]);

const meta = ref({});
const people = ref([]);
const editing = ref("");
const draft = ref("");
const saving = ref(false);
const error = ref("");
const editor = ref(null);

const entries = computed(() =>
	props.details
		.filter((detail) => !detail.when || detail.when(props.doc))
		.map((detail) => {
			const fieldMeta = meta.value[detail.field];
			const control = controlFor(fieldMeta);
			const raw = props.doc[detail.field];
			const value = detail.show
				? detail.show(props.doc)
				: readValue(fieldMeta || { fieldtype: "Data" }, raw, nameOf);
			const editable =
				Boolean(fieldMeta) &&
				mayChangeField(detail.field, { mayEdit: props.mayEdit, people: people.value });
			return {
				key: detail.field,
				field: detail.field,
				label: detail.label || fieldMeta?.label || detail.field,
				value,
				editable,
				control,
				meta: fieldMeta,
				wide: detail.wide || control === "note",
				options:
					control === "person"
						? [
								// An optional person (the reviewer) may be cleared.
								...(fieldMeta.reqd ? [] : [{ label: "—", value: "" }]),
								...personOptions(people.value),
						  ]
						: control === "select"
						? selectOptions(fieldMeta)
						: [],
			};
		})
		.filter((entry) => entry.value || entry.editable)
);
// Fields with nothing in them yet, which only those who may fill them in see.
const showEmpty = ref(false);
const empty = computed(() => entries.value.filter((entry) => !entry.value));
const shown = computed(() =>
	entries.value.filter(
		(entry) => entry.value || showEmpty.value || editing.value === entry.field
	)
);

async function start(entry) {
	editing.value = entry.field;
	draft.value = editValue(entry.meta, props.doc[entry.field]);
	error.value = "";
	await nextTick();
	// frappe-ui's select is a button that opens its list; the others are inputs.
	const control = editor.value?.[0]?.querySelector("input, textarea, button");
	control?.focus();
	// A date opens its calendar, and a choice its list (as the down arrow opens it), at once.
	if (entry.control === "date") control?.click();
	if (entry.control === "select" || entry.control === "person") {
		control?.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
	}
}

function cancel() {
	editing.value = "";
	error.value = "";
}

function saveNow(value) {
	draft.value = value;
	save();
}

async function save() {
	const entry = entries.value.find((candidate) => candidate.field === editing.value);
	if (!entry || saving.value) return;
	const change = changeFor(entry.meta, props.doc[entry.field], draft.value);
	if (change === null) return cancel();
	if (entry.meta.reqd && !change) {
		error.value = `${entry.label} cannot be left empty.`;
		return;
	}
	saving.value = true;
	error.value = "";
	try {
		await saveChanges(
			props.doctype,
			props.name,
			{ [entry.field]: change },
			props.doc.modified
		);
		editing.value = "";
		emit("saved");
	} catch (err) {
		if (err.isNetwork) {
			error.value = "Changing details needs a connection to the server.";
		} else {
			error.value = err.message;
			// Someone else changed it: show the record as it is now, with this field still open.
			if (err.isConflict) emit("saved");
		}
	} finally {
		saving.value = false;
	}
}

onMounted(async () => {
	try {
		const options = await call("kxcompliance.api.editable_fields", { doctype: props.doctype });
		meta.value = options.fields;
		people.value = options.people;
	} catch {
		// Without them the details still show; they cannot be changed here until it loads.
		meta.value = {};
	}
});
</script>
