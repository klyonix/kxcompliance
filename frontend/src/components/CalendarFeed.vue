<template>
	<section class="flex flex-col gap-3" aria-labelledby="calendar-heading">
		<h2 id="calendar-heading" class="text-base font-semibold text-ink-gray-8">Calendar</h2>
		<p class="text-base text-ink-gray-6">
			{{
				clientLogin
					? "See your filing due dates and the documents your firm needs in Google Calendar or Outlook."
					: "See your filings, expiries, hearings and document requests in Google Calendar or Outlook."
			}}
			It updates by itself every few hours.
		</p>

		<p v-if="error" role="alert" class="text-base text-ink-red-4">{{ error }}</p>
		<Skeleton v-else-if="!settings" class="h-9 w-48 rounded-lg" />

		<template v-else>
			<TabButtons
				v-if="settings.may_choose_scope"
				:model-value="settings.scope"
				:options="SCOPES"
				@update:model-value="(scope) => change({ scope })"
			/>

			<div v-if="!settings.url">
				<Button
					variant="solid"
					icon-left="lucide-calendar-plus"
					label="Get calendar link"
					:loading="busy"
					@click="change({ scope: settings.scope })"
				/>
			</div>

			<template v-else>
				<div class="flex gap-2">
					<TextInput
						:model-value="settings.url"
						readonly
						class="min-w-0 flex-1"
						aria-label="Your calendar link"
						@focus="$event.target.select()"
					/>
					<Button icon-left="lucide-copy" label="Copy" @click="copy" />
				</div>
				<div class="flex flex-wrap gap-2">
					<Button
						label="Add to Google Calendar"
						:href="googleLink(settings.url)"
						target="_blank"
					/>
					<Button
						label="Add to Outlook"
						:href="outlookLink(settings.url, boot.appName)"
						target="_blank"
					/>
				</div>
				<p class="text-sm text-ink-gray-5">
					Keep the link to yourself: anyone who has it can see this calendar. If it may
					have been shared, make a new one; the old link stops working.
				</p>
				<div class="flex flex-wrap gap-2">
					<Button
						variant="ghost"
						label="Make a new link"
						:disabled="busy"
						@click="newLink"
					/>
					<Button
						variant="ghost"
						theme="red"
						label="Stop the calendar"
						:disabled="busy"
						@click="stop"
					/>
				</div>
			</template>
		</template>
	</section>
</template>

<script setup>
// The person's calendar feed: get the link, add it to a calendar app, renew or stop it.
import { onMounted, ref } from "vue";
import { Button, Skeleton, TabButtons, TextInput, toast } from "frappe-ui";
import { call } from "@/api";
import { boot, isClientLogin } from "@/boot";
import { googleLink, outlookLink } from "@/lib/calendarFeed";

const SCOPES = [
	{ label: "My work", value: "My Work" },
	{ label: "Everything I can see", value: "Everything I Can See" },
];
const METHOD = "kxcompliance.kx_compliance.calendar_feed";

const clientLogin = isClientLogin();
const settings = ref(null);
const busy = ref(false);
const error = ref("");

const friendly = (err) =>
	err.isNetwork
		? "That did not reach the server. Try again when you are back online."
		: err.message;

async function run(method, params = {}) {
	busy.value = true;
	error.value = "";
	try {
		return await call(`${METHOD}.${method}`, params, { httpMethod: "POST" });
	} catch (err) {
		error.value = friendly(err);
		return null;
	} finally {
		busy.value = false;
	}
}

async function change(params) {
	const answer = await run("set_up_feed", params);
	if (answer) settings.value = answer;
}

function newLink() {
	if (!window.confirm("Make a new link? The calendar using the old one stops updating.")) return;
	change({ scope: settings.value.scope, new_link: true });
}

async function stop() {
	if (!window.confirm("Stop the calendar? Calendar apps using the link stop updating.")) return;
	await run("stop_feed");
	if (!error.value) settings.value = { ...settings.value, url: "" };
}

async function copy() {
	await navigator.clipboard.writeText(settings.value.url);
	toast.success("Link copied");
}

onMounted(async () => {
	try {
		settings.value = await call(`${METHOD}.feed_settings`);
	} catch (err) {
		error.value = friendly(err);
	}
});
</script>
