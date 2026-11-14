<template>
	<Dialog
		v-model:open="open"
		:title="complete ? 'Complete renewal' : 'Record the renewal'"
		:actions="[
			{
				label: complete ? 'Complete renewal' : 'Save',
				variant: 'solid',
				onClick: ({ close }) => save(close),
			},
		]"
	>
		<form class="flex flex-col gap-4" @submit.prevent>
			<p class="text-base text-ink-gray-6">
				{{
					complete
						? `Completing it moves ${itemTitle} to the new dates and certificate.`
						: `Record what the authority issued; a Compliance Manager then completes it.`
				}}
			</p>
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
				<FormControl
					v-model="form.new_valid_from"
					type="date"
					:format="pickerFormat()"
					label="Valid from"
				/>
				<FormControl
					v-model="form.new_valid_until"
					type="date"
					:format="pickerFormat()"
					label="Valid until"
				/>
			</div>
			<div class="flex flex-col gap-1.5">
				<span class="text-xs text-ink-gray-5">New certificate</span>
				<div class="flex items-center gap-3 rounded-lg bg-surface-gray-1 px-3 py-2.5">
					<span class="min-w-0 flex-1 truncate text-base text-ink-gray-8">{{
						file?.name || certificateName || "None attached"
					}}</span>
					<Button
						:label="file || certificateName ? 'Replace' : 'Attach'"
						@click="input?.click()"
					/>
					<input
						ref="input"
						type="file"
						accept="image/*,application/pdf"
						class="hidden"
						@change="file = $event.target.files?.[0] || null"
					/>
				</div>
			</div>
			<FormControl v-model="form.fee" type="number" label="Fee paid" placeholder="0.00" />
			<p v-if="error" role="alert" class="text-base text-ink-red-4">{{ error }}</p>
		</form>
	</Dialog>
</template>

<script setup>
// Record a renewal's new validity and certificate, and for a manager, complete it.
import { computed, reactive, ref, watch } from "vue";
import { Button, Dialog, FormControl } from "frappe-ui";
import { saveChanges, upload } from "@/api";
import { pickerFormat } from "@/lib/format";

const props = defineProps({
	renewal: { type: Object, default: null },
	itemTitle: { type: String, default: "" },
	// A manager completing it; otherwise the holder records what was issued.
	complete: { type: Boolean, default: false },
});
const emit = defineEmits(["saved"]);
const open = defineModel("open", { type: Boolean, default: false });

const form = reactive({ new_valid_from: "", new_valid_until: "", fee: "" });
const file = ref(null);
const input = ref(null);
const error = ref("");

const certificateName = computed(() =>
	props.renewal?.new_certificate
		? decodeURIComponent(props.renewal.new_certificate.split("/").pop())
		: ""
);

watch(open, (now) => {
	if (!now || !props.renewal) return;
	Object.assign(form, {
		new_valid_from: props.renewal.new_valid_from || "",
		new_valid_until: props.renewal.new_valid_until || "",
		fee: props.renewal.fee || "",
	});
	file.value = null;
	error.value = "";
});

async function save(close) {
	error.value = "";
	try {
		const values = {
			new_valid_from: form.new_valid_from || null,
			new_valid_until: form.new_valid_until || null,
			fee: form.fee === "" ? 0 : Number(form.fee),
		};
		if (file.value) {
			const uploaded = await upload(file.value, {
				doctype: "Compliance Renewal",
				docname: props.renewal.name,
			});
			values.new_certificate = uploaded.file_url;
		}
		if (props.complete) values.status = "Approved";
		await saveChanges(
			"Compliance Renewal",
			props.renewal.name,
			values,
			props.renewal.modified
		);
		close();
		emit("saved", props.complete ? "Renewal completed" : "Renewal details saved");
	} catch (err) {
		error.value = err.isNetwork
			? "That did not reach the server. Try again when you are back online."
			: err.message;
	}
}
</script>
