<template>
	<section
		v-if="data?.show"
		class="flex flex-col gap-3 rounded-lg border border-outline-gray-2 px-4 py-4"
		aria-labelledby="getting-started-heading"
		data-tour="getting-started"
	>
		<div class="flex items-start justify-between gap-3">
			<div class="flex flex-col gap-0.5">
				<h2 id="getting-started-heading" class="text-base font-semibold text-ink-gray-8">
					Getting started
				</h2>
				<p class="text-sm text-ink-gray-5">{{ done }} of {{ data.steps.length }} done</p>
			</div>
			<Button variant="ghost" label="Hide" @click="hide" />
		</div>
		<div
			class="h-1.5 w-full overflow-hidden rounded-full bg-surface-gray-2"
			role="progressbar"
			:aria-valuenow="done"
			aria-valuemin="0"
			:aria-valuemax="data.steps.length"
			aria-label="Getting started"
		>
			<span
				class="block h-full rounded-full bg-surface-green-5"
				:style="{ width: `${(done * 100) / data.steps.length}%` }"
			/>
		</div>
		<ol class="flex flex-col">
			<li v-for="step in data.steps" :key="step.key">
				<RouterLink
					:to="ROUTES[step.key]"
					class="flex items-start gap-3 rounded-lg px-2 py-2 hover:bg-surface-gray-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4"
				>
					<span
						:class="
							step.done
								? 'lucide-circle-check text-ink-green-4'
								: 'lucide-circle text-ink-gray-4'
						"
						class="mt-0.5 size-5 shrink-0"
						aria-hidden="true"
					/>
					<span class="flex min-w-0 flex-col">
						<span
							class="text-base"
							:class="
								step.done
									? 'text-ink-gray-5 line-through'
									: 'font-medium text-ink-gray-8'
							"
							>{{ step.label
							}}<span class="sr-only">{{ step.done ? " (done)" : "" }}</span></span
						>
						<span v-if="!step.done" class="text-sm text-ink-gray-5">{{
							step.detail
						}}</span>
					</span>
				</RouterLink>
			</li>
		</ol>
	</section>
</template>

<script setup>
// The first-week checklist on a manager's My Work: each step opens the screen that does it and
// ticks itself once done. It goes away when everything is done, or when the manager hides it.
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { Button, toast } from "frappe-ui";
import { call } from "@/api";

const ROUTES = {
	company: { name: "Companies" },
	client: { name: "ClientNew" },
	colleague: { name: "People" },
	billing: { name: "BillingSettings" },
	privacy: { name: "Settings", query: { tab: "privacy" } },
	reminders: { name: "Settings" },
};

const data = ref(null);
const done = computed(() => data.value.steps.filter((step) => step.done).length);

async function hide() {
	data.value = { ...data.value, show: false };
	try {
		await call("kxcompliance.api.hide_getting_started", {}, { httpMethod: "POST" });
		toast.info("Hidden. Tours and help are under the question mark.");
	} catch {
		// Hidden for now; it may show again next time.
	}
}

onMounted(async () => {
	try {
		data.value = await call("kxcompliance.api.getting_started_checklist");
	} catch {
		// The checklist only helps; My Work works without it, offline included.
		data.value = null;
	}
});
</script>
