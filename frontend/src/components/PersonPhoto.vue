<template>
	<div class="flex items-center gap-3">
		<Avatar :image="image || undefined" :label="name" :size="size" />
		<div class="flex min-w-0 flex-col gap-2">
			<!-- What goes beside the photo, such as the person's name. -->
			<slot />
			<div v-if="editable" class="flex flex-wrap gap-2">
				<Button
					:label="image ? 'Change photo' : 'Add photo'"
					icon-left="lucide-camera"
					:loading="working"
					@click="input?.click()"
				/>
				<Button
					v-if="image"
					variant="ghost"
					label="Remove"
					:disabled="working"
					@click="remove"
				/>
			</div>
		</div>
		<input
			ref="input"
			type="file"
			accept="image/jpeg,image/png,image/webp,image/gif"
			class="hidden"
			:aria-label="`Photo of ${name}`"
			@change="pick"
		/>
	</div>
</template>

<script setup>
// Someone's photo beside their name, or their initials until one is added. Their own, or a
// manager's for anyone on the team, can be changed here.
import { ref } from "vue";
import { Avatar, Button, toast } from "frappe-ui";
import { call, uploadPersonPhoto } from "@/api";

const props = defineProps({
	user: { type: String, required: true },
	name: { type: String, required: true },
	size: { type: String, default: "2xl" },
	editable: { type: Boolean, default: true },
});
const image = defineModel({ type: String, default: "" });
const input = ref(null);
const working = ref(false);

async function pick(event) {
	const file = event.target.files?.[0];
	event.target.value = "";
	if (!file) return;
	working.value = true;
	try {
		image.value = (await uploadPersonPhoto(file, props.user)).user_image;
		toast.success("Photo saved");
	} catch (err) {
		toast.error(err.message);
	} finally {
		working.value = false;
	}
}

async function remove() {
	working.value = true;
	try {
		await call(
			"kxcompliance.api.remove_person_photo",
			{ user: props.user },
			{ httpMethod: "POST" }
		);
		image.value = "";
	} catch (err) {
		toast.error(err.message);
	} finally {
		working.value = false;
	}
}
</script>
