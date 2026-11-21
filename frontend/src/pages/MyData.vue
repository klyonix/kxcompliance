<template>
	<AppPageHeader
		:title="t('Your data')"
		:parent="{ label: t('Account'), route: { name: 'Account' } }"
	/>

	<div class="mx-auto flex w-full max-w-2xl flex-col gap-6 px-4 py-6 sm:px-6">
		<p class="text-base text-ink-gray-6">
			{{
				t(
					"Everything the app holds about you. Download it to keep a copy. To have something corrected or erased, ask from Account."
				)
			}}
		</p>
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<div v-else-if="!data" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton v-for="index in 5" :key="index" class="h-6 w-full rounded" />
		</div>
		<PersonalData v-else :data="data" />
	</div>
</template>

<script setup>
// What the app holds about the person reading it, any time (DPDP: the right to see one's data).
import { onMounted, ref } from "vue";
import { Skeleton } from "frappe-ui";
import { call } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import PersonalData from "@/components/PersonalData.vue";
import { t } from "@/lib/i18n";
import { notLoaded } from "@/offline/reachability";

const data = ref(null);
const error = ref("");

onMounted(async () => {
	try {
		data.value = await call("kxcompliance.api.my_personal_data");
	} catch (err) {
		error.value = err.isNetwork ? notLoaded(t("your data")) : err.message;
	}
});
</script>
