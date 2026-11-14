<template>
	<AppPageHeader title="Account" />

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-6 sm:px-6">
		<div class="flex items-center gap-3">
			<Avatar :label="boot.userFullname || boot.user" size="2xl" />
			<div class="flex min-w-0 flex-col">
				<p class="truncate text-lg font-semibold text-ink-gray-9">
					{{ boot.userFullname || boot.user }}
				</p>
				<p class="truncate text-base text-ink-gray-5">{{ boot.user }}</p>
			</div>
		</div>

		<section class="flex flex-col gap-3" aria-labelledby="appearance-heading">
			<h2 id="appearance-heading" class="text-base font-semibold text-ink-gray-8">
				Appearance
			</h2>
			<TabButtons
				:model-value="colorScheme"
				:options="[
					{ label: 'System', value: 'system' },
					{ label: 'Light', value: 'light' },
					{ label: 'Dark', value: 'dark' },
				]"
				@update:model-value="setColorScheme"
			/>
		</section>

		<section class="flex flex-col gap-3" aria-labelledby="sync-heading">
			<h2 id="sync-heading" class="text-base font-semibold text-ink-gray-8">
				Changes on this device
			</h2>
			<SyncStatus />
			<div
				v-for="entry in outbox.needsLook"
				:key="entry.id"
				class="flex flex-col gap-2 rounded-lg bg-surface-gray-1 p-3"
			>
				<p class="text-base font-medium text-ink-gray-8">
					{{ entry.doctype }} {{ entry.name }}
				</p>
				<p class="text-base text-ink-red-4">{{ entry.error }}</p>
				<div class="flex gap-2">
					<Button label="Send again" @click="sendAgain(entry)" />
					<Button variant="ghost" label="Discard" @click="drop(entry)" />
				</div>
			</div>
		</section>

		<div class="flex flex-col gap-2">
			<Button
				v-if="mayUseDesk()"
				label="Open the Desk"
				icon-left="lucide-app-window"
				class="justify-start"
				@click="openDesk"
			/>
			<Button
				label="Sign out"
				icon-left="lucide-log-out"
				class="justify-start"
				@click="leave"
			/>
		</div>
	</div>
</template>

<script setup>
import { Avatar, Button, TabButtons, useColorScheme } from "frappe-ui";
import { call } from "@/api";
import { boot, mayUseDesk } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import SyncStatus from "@/components/SyncStatus.vue";
import { signOut } from "@/navigation";
import { clearOutbox, outbox, refresh, sendWaiting } from "@/offline/outbox";
import { discard, retry } from "@/offline/queue";

const { colorScheme, setColorScheme } = useColorScheme();

// Send a change again against the record as it is now; the server still applies every rule.
async function sendAgain(entry) {
	const current = await call("frappe.client.get_value", {
		doctype: entry.doctype,
		filters: entry.name,
		fieldname: "modified",
	});
	await retry(entry, current.modified);
	await refresh();
	await sendWaiting();
}

async function drop(entry) {
	if (!window.confirm("Discard this change? It has not reached the server.")) return;
	await discard(entry);
	await refresh();
}

const openDesk = () => (window.location.href = "/app/compliance-plus");
const leave = () =>
	signOut({ unsent: outbox.waiting + outbox.needsLook.length, clear: clearOutbox });
</script>
