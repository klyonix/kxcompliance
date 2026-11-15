<template>
	<AppPageHeader
		v-if="!gated"
		title="Privacy notice"
		:parent="{ label: 'Account', route: { name: 'Account' } }"
	/>

	<div
		class="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-4 sm:px-6"
		:class="gated ? 'py-8 sm:py-12' : 'py-6'"
	>
		<div v-if="gated" class="flex flex-col gap-1">
			<p class="text-sm text-ink-gray-5">{{ t("Before you start") }}</p>
			<h1 class="text-2xl font-semibold text-ink-gray-9">
				{{ t("How your data is used") }}
			</h1>
			<p class="text-base text-ink-gray-6">
				{{
					t(
						"Read this once. You can read it again, ask about your data or withdraw from Account at any time."
					)
				}}
			</p>
		</div>

		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<div v-else-if="!notice" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton v-for="index in 5" :key="index" class="h-5 w-full rounded" />
		</div>
		<template v-else>
			<!-- Written by the site's managers and cleaned of scripts by the server when saved. -->
			<div
				class="prose prose-sm max-w-none rounded-lg border border-outline-gray-1 p-4 text-ink-gray-8 sm:p-6"
				data-tour="privacy-notice"
				v-html="notice.text"
			/>
			<p v-if="!gated" class="text-sm text-ink-gray-5">
				{{ t("Version {0}.", notice.version) }}
				{{
					notice.accepted
						? t("You have accepted it.")
						: t("You have not accepted it yet.")
				}}
			</p>
		</template>
	</div>

	<div
		v-if="gated && notice"
		class="sticky bottom-0 z-10 border-t border-outline-gray-1 bg-surface-base"
	>
		<div
			class="mx-auto flex w-full max-w-2xl flex-col-reverse gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-end sm:px-6"
		>
			<p v-if="saveError" role="alert" class="text-sm text-ink-red-4 sm:mr-auto">
				{{ saveError }}
			</p>
			<Button variant="ghost" :label="t('Sign out')" @click="leave" />
			<Button
				variant="solid"
				:label="t('I have read this and agree')"
				:loading="saving"
				@click="accept"
			/>
		</div>
	</div>
</template>

<script setup>
// The privacy notice: shown before anything else until the person accepts its current version,
// and readable again from Account.
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button, Skeleton } from "frappe-ui";
import { call } from "@/api";
import { boot } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { safeNext } from "@/lib/privacy";
import { signOut } from "@/navigation";
import { clearOutbox, outbox } from "@/offline/outbox";
import { notLoaded } from "@/offline/reachability";

const route = useRoute();
const router = useRouter();
// Sent here by the app before it may be used, rather than opened to read again.
const gated = computed(() => Boolean(route.query.next));
const notice = ref(null);
const error = ref("");
const saveError = ref("");
const saving = ref(false);

function goOn() {
	boot.privacyNoticeDue = false;
	router.replace(safeNext(route.query.next));
}

async function accept() {
	saveError.value = "";
	saving.value = true;
	try {
		await call(
			"kxcompliance.api.accept_privacy_notice",
			{ version: notice.value.version },
			{ httpMethod: "POST" }
		);
		goOn();
	} catch (err) {
		saveError.value = err.isNetwork
			? "Your answer did not reach the server. Try again when you are back online."
			: err.message;
		// The notice changed while it was being read: show the new one.
		if (!err.isNetwork) await load();
	} finally {
		saving.value = false;
	}
}

async function load() {
	try {
		notice.value = await call("kxcompliance.api.privacy_notice");
		// Accepted already, on another device or before this page was cached.
		if (gated.value && notice.value.accepted) goOn();
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("the privacy notice") : err.message;
	}
}

const leave = () =>
	signOut({ unsent: outbox.waiting + outbox.needsLook.length, clear: clearOutbox });

onMounted(load);
</script>
