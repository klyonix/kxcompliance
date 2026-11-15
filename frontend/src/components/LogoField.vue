<template>
	<div class="flex items-center gap-4">
		<img
			v-if="logo"
			:src="logo"
			:alt="alt"
			class="size-16 shrink-0 rounded-lg bg-surface-gray-1 object-contain p-1"
		/>
		<span
			v-else
			class="flex size-16 shrink-0 items-center justify-center rounded-lg bg-surface-gray-2 text-ink-gray-5"
			aria-hidden="true"
		>
			<span class="lucide-image size-6" />
		</span>
		<div class="flex flex-col gap-1">
			<span class="text-base text-ink-gray-8">{{ label }}</span>
			<div class="flex gap-2">
				<Button
					:label="logo ? 'Change logo' : 'Add logo'"
					:loading="uploading"
					@click="input?.click()"
				/>
				<Button v-if="logo" variant="ghost" label="Remove" @click="logo = ''" />
			</div>
		</div>
		<input ref="input" type="file" accept="image/*" class="hidden" @change="pick" />
	</div>
</template>

<script setup>
// A logo, uploaded as a public file (bills and statements print it) to the record it belongs to.
import { ref } from "vue";
import { Button, toast } from "frappe-ui";
import { upload } from "@/api";

const props = defineProps({
	label: { type: String, required: true },
	alt: { type: String, default: "Logo" },
	// The record the file is attached to.
	doctype: { type: String, required: true },
	docname: { type: String, required: true },
});
const logo = defineModel({ type: String, default: "" });
const input = ref(null);
const uploading = ref(false);

async function pick(event) {
	const file = event.target.files?.[0];
	event.target.value = "";
	if (!file) return;
	uploading.value = true;
	try {
		const uploaded = await upload(file, {
			doctype: props.doctype,
			docname: props.docname,
			isPrivate: false,
		});
		logo.value = uploaded.file_url;
	} catch (err) {
		toast.error(err.message);
	} finally {
		uploading.value = false;
	}
}
</script>
