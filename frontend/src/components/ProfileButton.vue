<template>
	<button
		type="button"
		class="flex w-full items-center gap-2 rounded-md p-1 text-left hover:bg-surface-gray-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4"
		:aria-label="`Your profile: ${name}`"
		data-tour="profile"
		@click="open = true"
	>
		<Avatar :image="profile.image || undefined" :label="name" size="md" />
		<span v-if="!collapsed" class="flex min-w-0 flex-col">
			<span class="truncate text-sm font-medium text-ink-gray-8">{{ name }}</span>
			<span class="truncate text-xs text-ink-gray-5">{{ role }}</span>
		</span>
	</button>

	<Dialog v-model:open="open" title="Your profile">
		<div class="flex flex-col gap-5">
			<PersonPhoto v-model="profile.image" :user="boot.user" :name="name" />
			<dl class="grid grid-cols-[5rem_1fr] gap-x-4 gap-y-2 text-base">
				<dt class="text-ink-gray-5">Name</dt>
				<dd class="truncate text-ink-gray-8">{{ name }}</dd>
				<dt class="text-ink-gray-5">Email</dt>
				<dd class="truncate text-ink-gray-8">{{ boot.user }}</dd>
				<dt class="text-ink-gray-5">Role</dt>
				<dd class="text-ink-gray-8">{{ role }}</dd>
			</dl>
			<div class="flex flex-col gap-2 sm:flex-row">
				<Button
					label="Account and appearance"
					icon-left="lucide-settings-2"
					:route="{ name: 'Account' }"
					@click="open = false"
				/>
				<Button
					variant="ghost"
					label="Sign out"
					icon-left="lucide-log-out"
					@click="leave"
				/>
			</div>
		</div>
	</Dialog>
</template>

<script setup>
// At the foot of the side bar: who is signed in, with their photo or initials. It opens their
// profile, to change the photo, open Account or sign out.
import { ref } from "vue";
import { Avatar, Button, Dialog } from "frappe-ui";
import { boot, profile } from "@/boot";
import PersonPhoto from "@/components/PersonPhoto.vue";
import { roleLabel } from "@/lib/people";
import { signOut } from "@/navigation";
import { clearOutbox, outbox } from "@/offline/outbox";

defineProps({ collapsed: { type: Boolean, default: false } });

const open = ref(false);
const name = boot.userFullname || boot.user;
const role = roleLabel(boot.roles);

function leave() {
	open.value = false;
	signOut({ unsent: outbox.waiting + outbox.needsLook.length, clear: clearOutbox });
}
</script>
